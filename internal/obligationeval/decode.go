package obligationeval

import (
	"bytes"
	"encoding/json"
	"fmt"
	"reflect"
	"strings"
	"unicode/utf8"
)

func decode(data []byte, destination interface{}) error {
	if !utf8.Valid(data) || !json.Valid(data) {
		return fmt.Errorf("invalid UTF-8 JSON")
	}
	if err := shape(data, reflect.TypeOf(destination).Elem(), "$"); err != nil {
		return err
	}
	return json.Unmarshal(data, destination)
}

func shape(data []byte, kind reflect.Type, path string) error {
	if kind == reflect.TypeOf(json.RawMessage{}) {
		return nil
	}
	if kind.Kind() == reflect.Pointer {
		kind = kind.Elem()
	}
	switch kind.Kind() {
	case reflect.Struct:
		decoder := json.NewDecoder(bytes.NewReader(data))
		token, err := decoder.Token()
		if err != nil || token != json.Delim('{') {
			return fmt.Errorf("%s: expected object", path)
		}
		fields := map[string]reflect.StructField{}
		for i := 0; i < kind.NumField(); i++ {
			field := kind.Field(i)
			fields[strings.Split(field.Tag.Get("json"), ",")[0]] = field
		}
		seen := map[string]bool{}
		for decoder.More() {
			key, err := decoder.Token()
			if err != nil {
				return err
			}
			name, ok := key.(string)
			if !ok {
				return fmt.Errorf("%s: invalid key", path)
			}
			field, exists := fields[name]
			if !exists || seen[name] {
				return fmt.Errorf("%s.%s: unknown or duplicate field", path, name)
			}
			seen[name] = true
			var raw json.RawMessage
			if err := decoder.Decode(&raw); err != nil {
				return err
			}
			if bytes.Equal(bytes.TrimSpace(raw), []byte("null")) {
				if field.Tag.Get("nullable") != "true" {
					return fmt.Errorf("%s.%s: null is not allowed", path, name)
				}
				continue
			}
			if err := shape(raw, field.Type, path+"."+name); err != nil {
				return err
			}
		}
		for i := 0; i < kind.NumField(); i++ {
			field := kind.Field(i)
			name := strings.Split(field.Tag.Get("json"), ",")[0]
			if !seen[name] && field.Tag.Get("optional") != "true" {
				return fmt.Errorf("%s.%s: required field missing", path, name)
			}
		}
	case reflect.Slice:
		if len(data) == 0 || bytes.TrimSpace(data)[0] != '[' {
			return fmt.Errorf("%s: expected array", path)
		}
		var rows []json.RawMessage
		if err := json.Unmarshal(data, &rows); err != nil {
			return err
		}
		for i, raw := range rows {
			if err := shape(raw, kind.Elem(), fmt.Sprintf("%s[%d]", path, i)); err != nil {
				return err
			}
		}
	case reflect.String:
		if len(data) == 0 || bytes.TrimSpace(data)[0] != '"' {
			return fmt.Errorf("%s: expected string", path)
		}
	case reflect.Bool:
		if string(data) != "true" && string(data) != "false" {
			return fmt.Errorf("%s: expected boolean", path)
		}
	}
	return nil
}

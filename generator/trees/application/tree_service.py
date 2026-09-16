from __future__ import annotations

import typing

import tesser.application as ts

import trees.application.ports as ports
import trees.client as client
import trees.domain as domain


class MapToGenerationPathsSpec(ts.Mapper, domain.GenerationPathsSpec):

    def __init__(self, generate_tree_request: client.GenerateTreeRequest) -> None:
        super().__init__(spec_path=generate_tree_request.spec_path, out_dir=generate_tree_request.out_dir)


class MapToReadGenerationRequest(ts.Mapper, ports.ReadGenerationRequest):

    def __init__(self, generation_paths: domain.GenerationPaths) -> None:
        super().__init__(spec_path=str(generation_paths.spec_path()), out_dir=str(generation_paths.out_dir()))


class MapToTreeSpec(ts.Mapper, domain.TreeSpec):

    def __init__(self, read_generation_response: ports.ReadGenerationResponse) -> None:
        super().__init__(
            state=read_generation_response.spec.state.value,
            note=read_generation_response.spec.note,
            unknown_keys=read_generation_response.spec.unknown_keys,
            target=read_generation_response.target.state.value,
            app_name=read_generation_response.spec.app_name,
            bounded_context_name=read_generation_response.spec.bounded_context_name,
            aggregate_root_class_name=read_generation_response.spec.aggregate_root_class_name,
            durable_execution_engine=read_generation_response.spec.durable_execution_engine,
            database=read_generation_response.spec.database,
            identity_field_name=read_generation_response.spec.identity_field_name,
            identity_port_operation_name=read_generation_response.spec.identity_port_operation_name,
            aggregate_fields=tuple(
                (field_record.name, field_record.kind)
                for field_record in read_generation_response.spec.aggregate_fields
            ),
            sample_values=tuple(
                (
                    sample_record.name,
                    tuple((value_record.kind, value_record.text) for value_record in sample_record.values),
                )
                for sample_record in read_generation_response.spec.sample_values
            ),
            write_operation_name=read_generation_response.spec.write_operation_name,
            read_operation_name=read_generation_response.spec.read_operation_name,
            read_response_fields=read_generation_response.spec.read_response_fields,
            orchestrator_operation_name=read_generation_response.spec.orchestrator_operation_name,
            action_operation_name=read_generation_response.spec.action_operation_name,
            save_operation_name=read_generation_response.spec.save_operation_name,
            load_operation_name=read_generation_response.spec.load_operation_name,
            load_response_collection_name=read_generation_response.spec.load_response_collection_name,
            test_class_name=read_generation_response.spec.test_class_name,
            test_method_name=read_generation_response.spec.test_method_name,
            asserted_field=read_generation_response.spec.asserted_field,
            random_values=tuple(
                (value_record.kind, value_record.text) for value_record in read_generation_response.spec.random_values
            ),
            storage_url_variable=read_generation_response.spec.storage_url_variable,
            restate_ingress_url_variable=read_generation_response.spec.restate_ingress_url_variable,
            templates=tuple(
                (template_record.path, template_record.text)
                for template_record in read_generation_response.templates
            ),
        )


class MapToWriteTreeRequest(ts.Mapper, ports.WriteTreeRequest):

    def __init__(self, generation_paths: domain.GenerationPaths, tree: domain.Tree) -> None:
        super().__init__(
            out_dir=str(generation_paths.out_dir()),
            files=tuple(
                ports.FileRecord(path=str(generated_file.path()), text=str(generated_file.content()))
                for generated_file in tree.files()
            ),
        )


class MapToGenerateTreeResponseWhenWritten(ts.Mapper, client.GenerateTreeResponse):

    def __init__(self, write_tree_response: ports.WriteTreeResponse) -> None:
        super().__init__(problems=(), paths=write_tree_response.paths)


class MapToGenerateTreeResponseWithProblems(ts.Mapper, client.GenerateTreeResponse):

    def __init__(self, tree: domain.Tree) -> None:
        super().__init__(problems=tuple(str(text) for text in tree.problems()), paths=())


class TreeService(ts.ApplicationService):

    def __init__(self, generation_reader: ports.GenerationReader, tree_writer: ports.TreeWriter) -> None:
        self._generation_reader = generation_reader
        self._tree_writer = tree_writer

    def generate_tree(self, generate_tree_request: client.GenerateTreeRequest) -> client.GenerateTreeResponse:
        generation_paths = domain.GenerationPaths(MapToGenerationPathsSpec(generate_tree_request))
        read_generation_response = self._generation_reader.read_generation(
            MapToReadGenerationRequest(generation_paths)
        )
        tree = domain.Tree(MapToTreeSpec(read_generation_response))
        match tree.health():
            case domain.Health.CLEAN:
                write_tree_response = self._tree_writer.write_tree(MapToWriteTreeRequest(generation_paths, tree))
                return MapToGenerateTreeResponseWhenWritten(write_tree_response)
            case domain.Health.PROBLEMS:
                return MapToGenerateTreeResponseWithProblems(tree)
            case _ as never:
                typing.assert_never(never)

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
            target=read_generation_response.target.state.value,
            app=read_generation_response.spec.app,
            context=read_generation_response.spec.context,
            aggregate=read_generation_response.spec.aggregate,
            engine=read_generation_response.spec.engine,
            store=read_generation_response.spec.store,
            identity=read_generation_response.spec.identity,
            minted_by=read_generation_response.spec.minted_by,
            fields=tuple(
                (field_record.name, field_record.kind) for field_record in read_generation_response.spec.fields
            ),
            write=read_generation_response.spec.write,
            read=read_generation_response.spec.read,
            read_answers=read_generation_response.spec.read_answers,
            orchestrator=read_generation_response.spec.orchestrator,
            action=read_generation_response.spec.action,
            save=read_generation_response.spec.save,
            load=read_generation_response.spec.load,
            asserts=read_generation_response.spec.asserts,
            storage_env=read_generation_response.spec.storage_env,
            ingress_env=read_generation_response.spec.ingress_env,
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

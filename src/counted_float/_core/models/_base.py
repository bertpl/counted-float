from pydantic import BaseModel


class JsonReprModel(BaseModel):
    """A pydantic model that renders itself as indented JSON, for repr, str and show().

    Purely presentational: pydantic already handles serialization, this only decides what a model
    looks like when a human prints one.
    """

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return self.model_dump_json(indent=4)

    def show(self) -> None:
        print(self.model_dump_json(indent=4))

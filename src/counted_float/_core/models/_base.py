from pydantic import BaseModel


class MyBaseModel(BaseModel):
    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return self.model_dump_json(indent=4)

    def show(self) -> None:
        print(self.model_dump_json(indent=4))

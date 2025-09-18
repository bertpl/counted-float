from pydantic import BaseModel


class MyBaseModel(BaseModel):
    def __repr__(self):
        return str(self)

    def __str__(self):
        return self.model_dump_json(indent=4)

    def show(self):
        print(self.model_dump_json(indent=4))

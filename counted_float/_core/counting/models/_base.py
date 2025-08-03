from pydantic import BaseModel


class MyBaseModel(BaseModel):
    def print(self):
        print(self.model_dump_json(indent=4))

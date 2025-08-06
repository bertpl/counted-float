from pydantic import BaseModel


class MyBaseModel(BaseModel):
    def show(self):
        print(self.model_dump_json(indent=4))

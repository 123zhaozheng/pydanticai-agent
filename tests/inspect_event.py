
from pydantic_ai.messages import FunctionToolResultEvent
import inspect

print("Fields of FunctionToolResultEvent:")
try:
    # It might be a dataclass or pydantic model
    print(FunctionToolResultEvent.__annotations__)
except:
    pass

print("\nDir:")
print(dir(FunctionToolResultEvent))

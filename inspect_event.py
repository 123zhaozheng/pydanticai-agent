from pydantic_ai import FunctionToolResultEvent, FunctionToolCallEvent
import dataclasses

print("FunctionToolCallEvent fields:")
for f in dataclasses.fields(FunctionToolCallEvent):
    print(f"- {f.name}")

print("\nFunctionToolResultEvent fields:")
for f in dataclasses.fields(FunctionToolResultEvent):
    print(f"- {f.name}")

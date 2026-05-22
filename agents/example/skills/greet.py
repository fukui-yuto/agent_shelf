# ---
# description: Greet a user by name
# parameters:
#   name: string - Name of the person to greet
# ---

def run(name: str) -> dict:
    return {"message": f"Hello, {name}! Welcome to agent-shelf."}

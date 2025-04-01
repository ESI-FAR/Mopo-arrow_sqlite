import json
import subprocess

def test_array_numbers():
    input = """
        {
            "type": "array",
            "data": [2.3, 23.0, 5.0]
        }
    """.strip()

    output = """
        [
          {
            "name": "i",
            "values": [
              2.3,
              23.0,
              5.0
            ],
            "value_type": "number",
            "type": "array"
          }
        ]
    """.replace(" ","").replace("\n", "")
    command = f"echo '{input}' | python -m schema.reencode"
    result = subprocess.check_output(command, shell=True, text=True).strip()

    assert result == output

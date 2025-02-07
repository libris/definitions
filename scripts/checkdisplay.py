import json
from pathlib import Path

project_dir = Path(__file__).parent.parent
displaypath = project_dir / "source/vocab/display.jsonld"

with displaypath.open() as f:
    display = json.load(f)

for group in display["lensGroups"].values():
    if g_id := group.get("@id"):
        print(g_id)
    for key, lens in group.get("lenses", {}).items():
        cld = lens.get("classLensDomain")
        if key != cld:
            if cld is None:
                print(f"    {key} - Missing classLensDomain")
            else:
                print(f"    {key} - Different classLensDomain: {cld}")
    print()

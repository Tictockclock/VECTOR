'''
Bootstrap which imports all custom modules built for VECTOR
https://stackoverflow.com/questions/6465549/import-paths-the-right-way

Modify the environment variable with .bashrc:
`export VECTOR_ROOT=/absolute/path/to/our/repository`
or
`export VECTOR_ROOT=$(pwd)`

To use in our files:
```
import os; import sys
VECTOR_ROOT = os.getenv("VECTOR_ROOT")
sys.path.insert(0, VECTOR_ROOT) if (VECTOR_ROOT is not None) and (VECTOR_ROOT not in sys.path) else None
import setup; setup.loadModules()
```

Dimitry Melnikov, 2/17/25
'''

import sys
import os

def loadModules():
    VECTOR_ROOT = os.getenv("VECTOR_ROOT")

    if not VECTOR_ROOT:
        print("VECTOR_ROOT UNDEFINED! This run will likely fail")
        print("From VECTOR entrypoint, run `export VECTOR_ROOT=$(pwd)`")
        return # Avoid modifying sys.path with None values

    else:
        paths = [
                'bs/demo/graphing',   # Graphing Library
                'bs/nav/processing',  # Processing Library
                ]

        for p in paths:
            full_path = os.path.join(VECTOR_ROOT, p)
            if full_path not in sys.path:
                sys.path.append(full_path)
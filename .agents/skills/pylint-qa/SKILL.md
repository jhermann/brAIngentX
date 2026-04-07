---
name: pylint-qa
description: 'Performs static code analysis and PEP 8 validation on Python files. Returns a quality score and a list of specific violations (Errors, Warnings, Conventions).'
version: 1.0.0
author: Gemini
license: MIT
compatibility:
  runtime: python3
  dependencies:
    - pylint
metadata:
  category: quality-assurance
  priority: high
  tags: ["linting", "python", "pep8", "code-review"]
---

# SKILL: Python Code Quality Auditor

## 📝 Description
This skill allows the agent to perform static code analysis on Python files or directories using `pylint`. It identifies syntax errors, bugs, and stylistic departures from **PEP 8**, providing a numerical score (0.0 to 10.0) to quantify code health.

## ⚙️ Configuration
* **Script Name:** `call_pylint.py`
* **Dependency:** `pylint`
* **Environment:** Python 3.x

### Prerequisites
Before execution, ensure the environment has the necessary package installed:
```bash
pip install pylint
```

---

## 🛠️ Implementation (`call_pylint.py`)

```python
import subprocess
import sys
import re
import json

def lint_python_code(path: str):
    """
    Executes pylint on the provided path and returns a structured JSON result.
    """
    try:
        # Run pylint with exit-zero to prevent the shell from throwing an error code
        result = subprocess.run(
            [sys.executable, "-m", "pylint", path, "--exit-zero"],
            capture_output=True,
            text=True,
            check=True
        )
        
        output = result.stdout
        
        # Regex to capture the rating (e.g., 8.5/10)
        score_match = re.search(r"rated at (-?\d+\.\d+)/10", output)
        score = float(score_match.group(1)) if score_match else None
        
        response = {
            "success": True,
            "path": path,
            "score": score,
            "report": output.strip()
        }
        return json.dumps(response)

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

if __name__ == "__main__":
    # Expects path as the first argument
    if len(sys.argv) > 1:
        print(lint_python_code(sys.argv[1]))
```

---

## 🚀 Usage Guide

### Agent Instructions
The agent should invoke this skill whenever Python code is created, modified, or before a pull request is finalized.

**Input Schema:**
* `path` (string): The file path (e.g., `"src/main.py"`) or directory (e.g., `"tests/"`) to audit.

**Output Schema:**
* `success` (boolean): Whether the linting process finished.
* `score` (float): The code quality rating out of 10.
* `report` (string): The detailed list of violations and suggestions.

---

## 📋 Expected Behavior & Thresholds

| Score | Status | Action Required |
| :--- | :--- | :--- |
| **9.0 - 10.0** | ✅ Excellent | No action needed. Code is production-ready. |
| **7.0 - 8.9** | ⚠️ Acceptable | Agent should attempt to fix "Convention" or "Refactor" messages. |
| **Below 7.0** | ❌ Failed | Agent **must** refactor the code to address "Errors" and "Warnings" before proceeding. |

> [!TIP]
> If the score is low, the agent should look specifically for `E` (Error) and `W` (Warning) codes in the report first, as these impact functionality and safety more than stylistic conventions (`C`).

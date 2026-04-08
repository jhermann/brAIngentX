---
license: Apache 2.0
---
# brAIngentX<!-- omit from toc -->

> ![A futuristic armored head shot in a sleek metallic suit with glowing blue and purple highlights. Radiating lines surround the figure.](assets/brAIngentX-logo.png)<br/>
>   *Skills sharing for an agentic age.*

**Contents**

- [👀 Project Overview](#-project-overview)
- [📋 What Skills Are Supported?](#-what-skills-are-supported)
- [🚀 How Do I Use This?](#-how-do-i-use-this)
- [⚙️ How Does It Work?](#️-how-does-it-work)

## 👀 Project Overview
*brAIngentX* is focused on **Agentic AI**, where autonomous scripts manage tasks
like real-time data analysis, automated trading, or code repository maintenance
without constant human intervention.

This project offers a selection of general-purpose skills and tools to manage them,
across multiple projects (repositories) covering diverse topics. The goal of skills
management is to serve all of them by easy skill integration, but with allowing 
purposeful selection instead of one size fits all.

This is designed for and tested with *VS Code* and *GitHub Copilot*, but that does not
mean it won't work with other common IDEs and models.

## 📋 What Skills Are Supported?

The following skills are included in this repository. You can enable or use them as needed, on a per-project basis:

- 🏛️ **markdown-style**: Markdown Style Standards
- 🛠️ **pylint-qa**: Performs static code analysis and PEP 8 validation on Python files. Returns a quality score and a list of specific violations (Errors, Warnings, Conventions).
- 🏛️ **python-style**: Python Coding Style Standards
- 🏛️ **python-tests**: Pytest Testing Standards
- 🏛️ **secure-development**
- 🚧 An expert helping you to create and maintain an `AGENTS.md` file.

## 🚀 How Do I Use This?

To the repository you want to use the skills in, add this to your README or some other document with setup instructions.

```markdown
## ⚙️ Setup

1. Clone the [brAIngentX](https://github.com/jhermann/brAIngentX#readme) skills sharing repo, and call its `./install.sh` to symlink the `braingentx` tool into your local `bin` folder.
2. Go back to this repo's workdir and call `braingentx install markdown-style`. Call `braingentx list` to show more skills you might want to activate.
```

Then follow those instructions.

## ⚙️ How Does It Work?

🚧 TODO

To install `uv` and `uvx`, use `mkvenv3 uv uv uv.build`.

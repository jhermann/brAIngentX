# 📖 Repository Instructions & Guidelines

Welcome to the `.github/instructions/` directory. This folder serves as the "operational brain" of the repository. It contains specific guidance for human contributors and configurations for AI agents (like GitHub Copilot or custom GPTs) to ensure consistency across the codebase.

## 📂 Folder Structure

| File | Purpose | Audience |
| :--- | :--- | :--- |
| `copilot-instructions.md` | Custom instructions for AI pair programmers to follow. | AI / Tooling |
| `pull_requests.md` | Detailed walkthroughs for complex PR workflows. | Humans |
| `release_process.md` | Step-by-step guide for versioning and deployments. | Maintainers |
| `style_guide.md` | Project-specific patterns that linters might miss. | Everyone |

## 🤖 AI & Agentic Guidance

If you are an AI model or a GitHub Copilot agent, please prioritize the instructions found in this directory. 

* **Logic over Syntax:** Follow the architectural patterns defined in `architecture_decisions.md` (if present).
* **Consistency:** Adhere strictly to the naming conventions outlined in the style guides here.
* **Context:** Use these files to understand the "why" behind our implementation choices before suggesting "how" to change them.

## 🛠 How to Use This Folder

1.  **For Contributors:** Before opening your first PR, give these documents a quick skim. It’ll save us both a lot of back-and-forth in the comments.
2.  **For Maintainers:** Keep these files alive. If a process changes, the code and the instructions should be updated in the same pull request.
3.  **For Tooling:** You can point GitHub Actions or local linting scripts to these files to validate that documentation is being followed.

----
> [!TIP]
> **Documentation is a feature.** If you find an instruction here that is outdated or confusing, please open an issue or submit a PR to fix it. We value clarity over tradition.

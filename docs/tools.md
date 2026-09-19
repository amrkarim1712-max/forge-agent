# Tool system

Tools are registered with a name, description, JSON input schema, handler, and permission level.

| Tool | Purpose | Default permission |
| --- | --- | --- |
| `read_file` | Read bounded UTF-8 text | Safe |
| `write_file` | Create or replace a file | Review |
| `edit_file` | Replace one unambiguous text occurrence | Review |
| `line_edit` | Replace an inclusive line range | Review |
| `apply_patch` | Apply a validated unified diff | Review |
| `delete_file` | Delete one file | Review |
| `move_file` | Move one file | Review |
| `list_directory` | List project files | Safe |
| `search_files` | Search text files | Safe |
| `search_text` | Search alias for natural-language callers | Safe |
| `find_symbol` | Query the lightweight code index | Safe |
| `run_command` | Run a bounded shell command | Review or blocked by command |
| `run_script` | Run an existing workspace script | Review |
| `run_tests` | Detect and run a test command | Safe |
| `run_linter` | Detect and run linting | Safe |
| `run_formatter` | Detect and run formatting checks | Safe |
| `run_type_checker` | Detect and run type checks | Safe |
| `git_status` | Read Git status | Safe |
| `git_diff` | Read unstaged changes | Safe |
| `git_log` | Read recent history | Safe |
| `git_branch` / `git_show` | Read branch and object details | Safe |
| `git_add` / `git_commit` | Stage or commit local changes | Review |
| `web_search` | Query a configured real endpoint | Review |

Paths are normalized against the current project root. Traversal outside the root is rejected. The permission layer is a guard against accidental operations, not a security sandbox.

Every modifying tool can run in dry-run mode. File writes also support SHA-256 expectations so Forge can refuse to overwrite work that changed after inspection.
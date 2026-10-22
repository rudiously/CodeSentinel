# Component ownership
```mermaid
flowchart TD
 PR["GitHub PR"] --> Gate["Action or signed webhook"]
 Gate --> API["backend: orchestration"]
 API --> Model["model_service: inference"]
 API --> Tools["Static analyzers"]
 Model --> Risk["Pure risk policy"]
 Tools --> Risk
 Risk --> Store["Metadata database"]
 Store --> Dashboard["React dashboard"]
 Risk --> GitHub["Comment and check"]
```
Shared schemas own Contracts A/B. ML owns data/train/calibrate/export/register/explain. Deploy owns healthchecks, monitoring and image definitions. See Architecture.md for actual tree, status and decision log.

Model files are not bundled in this repository to keep the repo size manageable.

Expected files:
- model.onnx
- tokenizer.json
- config.json (optional, kept for reference)

Place them under the same directory as this README:
`src/main/resources/models/`

Suggested sources:
- sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (multilingual, ~420MB)
- onnx-models/all-MiniLM-L6-v2-onnx (English, ~80MB)

After downloading, rebuild the project to package the model into the shadow JAR.

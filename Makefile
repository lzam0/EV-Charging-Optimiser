# Used by `sam build` (Metadata.BuildMethod: makefile on ApiFunction in
# template.yaml). CodeUri for ApiFunction is the repo root because
# backend/main.py imports as "backend.routers...", "backend.services..." etc,
# and those absolute imports only resolve if the zip contains a real
# backend/ folder. A plain zip-the-whole-CodeUri build would also drag in
# frontend/node_modules (600MB+), blowing past Lambda's 250MB unzipped
# limit - .samignore does not apply to Python's pip builder, so this
# Makefile copies in only what the API Lambda actually needs.
build-ApiFunction:
	# --platform/--only-binary force pip to fetch manylinux wheels for
	# compiled deps (pydantic_core etc) even when building on macOS, since
	# Lambda runs Linux x86_64 and a locally-built wheel won't load there.
	pip install -r requirements.txt \
		--platform manylinux2014_x86_64 \
		--implementation cp \
		--python-version 3.12 \
		--only-binary=:all: \
		-t "$(ARTIFACTS_DIR)"
	cp -r backend "$(ARTIFACTS_DIR)/backend"
	cp -r pipeline "$(ARTIFACTS_DIR)/pipeline"
	rm -rf "$(ARTIFACTS_DIR)/backend/tests" "$(ARTIFACTS_DIR)/backend/venv"
	rm -rf "$(ARTIFACTS_DIR)/pipeline/venv" "$(ARTIFACTS_DIR)/pipeline/ingest/.local_raw"
	find "$(ARTIFACTS_DIR)" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

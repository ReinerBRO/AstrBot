```bash
bash scripts/upload-doc-images-to-r2.sh \
    --remote persbot-docs-s3 \
    --bucket persbot \
    --prefix docs \
    --rewrite-markdown \
    --public-base-url https://files.persbot.app
```
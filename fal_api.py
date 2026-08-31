"""Thin re-export. New code should import providers.fal."""
from providers.fal import (  # noqa: F401
    build_fal_input,
    fal_key,
    find_model,
    has_key,
    infer_image_fields,
    job_status,
    load_catalog,
    submit,
)

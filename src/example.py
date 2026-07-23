from osw_sanitizer import OSWSanitization, SanitizationConfig


INPUT_ZIP_FILE = "<OSW_DATASET_ZIP_FILE_PATH>"
OUTPUT_DIR = "<OUTPUT_DIRECTORY_PATH>"


def sanitize_with_defaults():
    sanitizer = OSWSanitization(
        input_path=INPUT_ZIP_FILE,
        output_dir=OUTPUT_DIR,
    )
    return sanitizer.sanitize()


def sanitize_with_config():
    config = SanitizationConfig(
        coordinate_precision=7,
        max_geometry_vertices=2000,
        allow_zero_length_lines=False,
    )
    sanitizer = OSWSanitization(
        input_path=INPUT_ZIP_FILE,
        output_dir=OUTPUT_DIR,
        config=config,
    )
    return sanitizer.sanitize()


if __name__ == "__main__":
    result = sanitize_with_config()
    print("Success:", result.success)
    print("Message:", result.message)
    print("Sanitized dataset:", result.updated_dataset_zip)
    print("Fixes JSON:", result.fixes_json)

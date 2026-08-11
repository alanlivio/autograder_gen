# autograder-gen

`autograder-gen` is a tool for lecturers to automatically generate assessment scripts for [Grading a Programming Assignment](https://guides.gradescope.com/hc/en-us/articles/22066635961357-Grading-a-Programming-Assignment) on Gradescope. It supports filling out an interactive web form or providing a YAML configuration, which then generates a packaged ZIP file ready to be uploaded to Gradescope.

The project validates your configuration, renders test scripts using Jinja2 templates, and packages everything for immediate upload to Gradescope.

## Setup

Set up the virtual environment and install all dependencies:

```bash
make venv
```

## CLI Usage

The Command-Line Interface allows you to generate autograders (`autograder.zip`) directly from a configuration file.

```bash
python autograder_gen/cli.py --config <path/to/config.yaml> [options]
```

### Arguments:

- `--config`, `-c` (required): Path to your configuration file (YAML).
- `--output`, `-o`: Output directory for the generated files (default: `./output`).
- `--with-description`, `-d`: Generate assessment documentation as `description.docx` alongside the ZIP.
- `--with-skeletons`, `-s`: Generate `correct_answer.zip` and `wrong_answer.zip` implementation skeletons.
- `--verbose`, `-v`: Enable verbose logging.

### Example:

```bash
python autograder_gen/cli.py --config tests/examples/py_simple/config.yaml --with-description --with-skeletons
```

## Web Interface

The web interface provides a graphical form to define your autograder structure or upload existing configurations. Start the Web Server:

```bash
python web/app.py
```

## Testing

To run the automated test suite and verify your installation:

```bash
python -m pytest
```

## Authors

- **Alan Guedes** – [@alanlivio](https://github.com/alanlivio)  
- **Giorgio Werberich Scur** – [@giorgioscur](https://github.com/giorgioscur)

## License

Contributions are welcome and will be credited. This project is licensed under the [MIT License](LICENSE).  
The University of Reading retains rights of original contributions.

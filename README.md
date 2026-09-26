# autograder_gen

`autograder_gen` is a tool for lecturers to automatically generate assessment scripts for [Grading a Programming Assignment](https://guides.gradescope.com/hc/en-us/articles/22066635961357-Grading-a-Programming-Assignment) on Gradescope. It supports filling out an interactive web form or providing a YAML configuration, which then generates a packaged ZIP file ready to be uploaded to Gradescope. The project validates your YAML configuration, renders test scripts using Jinja2 templates, and packages everything for immediate upload to Gradescope.

## Setup

Set up the virtual environment and install all dependencies:

```bash
make venv
```

## CLI Usage

The Command-Line Interface allows you to generate autograders directly from a configuration file. Generated assessment files (autograder.zip, stub submissions for testing) are created in the same folder as the config file.

```bash
python autograder_gen/cli.py --config <path/to/config.yaml> [options]
```

### Arguments:

- `--config`, `-c`: Path to your configuration file (YAML).
- `--descriptions`: Generate description.docx and description.md.
- `--run-submission`, `-r`: Path to submission directory or zip file to run using the configuration.
- `--run-stub-submissions`: Run autograder for generated stub submissions (stub_correct_answer.zip, stub_wrong_answer.zip, stub_compiler_error.zip, stub_correct_answer_wrong_location.zip).
- `--verbose`, `-v`: Print full autograder execution logs instead of only paths to log files.

### Examples:

Generate autograder package:

```bash
python autograder_gen/cli.py --config tests/examples/py_simple/config.yaml
```

Run a submission directory or zip against an autograder configuration:

```bash
python autograder_gen/cli.py --config tests/examples/py_simple/config.yaml --run-submission tests/examples/py_simple/correct_answer
```

Run autograder against generated stub submissions:

```bash
python autograder_gen/cli.py --config tests/examples/py_simple/config.yaml --run-stub-submissions
```

## Web Interface

The web interface provides a graphical form to define your autograder structure or upload existing configurations. Start the Web Server:

```bash
python autograder_gen/web/app.py
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

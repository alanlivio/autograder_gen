# wsgi

This folder contains configurations for WSGI deployment.

## Expected Symbolic Links at `/var/www/autograder/`

For deployment, `/var/www/autograder` should be a directory containing the following symbolic links pointing to the project files:

- `requirements.txt` -> `<project_root>/requirements.txt`
- `static` -> `<project_root>/autograder_gen/web/static`
- `autograder.wsgi` -> `<project_root>/autograder_gen/web/wsgi/autograder.wsgi`
- `autograder` -> `<project_root>`

## Deployments

### Local Development
For local development, you can run the following command to set up the directory structure and start a Gunicorn server:

```bash
make dev_deploy
```

### Production
For production environments, an Apache configuration with the following directive is expected:

```apache
WSGIScriptAlias / "/var/www/autograder/autograder.wsgi"
```

================================================================
 AI Code Maniac - Running in Docker (Beginner's Guide)
================================================================

This document explains, in plain language, how this Python project
runs inside a Docker container, why that is useful, and how to
update your code, mount your own folders, and manage the container.

If you have never used Docker before, read sections 1 and 2 first.

----------------------------------------------------------------
 TABLE OF CONTENTS
----------------------------------------------------------------
  1. What is Docker (in 60 seconds)
  2. Why use Docker for this project (advantages)
  3. The three files that make this work
  4. Build and start the container (the easy way)
  5. What actually happens when the container starts
  6. I changed a Python file - how do I update the container?
  7. Mounting a folder so the container can read your data
  8. Mounting a folder for live development (no rebuild needed)
  9. Common Docker commands you will use every day
 10. Troubleshooting checklist
 11. Cleaning up


================================================================
 1. WHAT IS DOCKER (IN 60 SECONDS)
================================================================

Think of Docker as a way to package an application together with
everything it needs to run - the right Python version, the right
libraries, the right system tools - into a single sealed box
called an "image".

When you "run" that image, Docker creates a live, running copy of
it called a "container". The container behaves like a tiny
isolated computer running just your app. It cannot see or break
the rest of your machine, and your machine cannot accidentally
break it.

Three words you will see again and again:

  - IMAGE     : the recipe / blueprint (built once, reused)
  - CONTAINER : a running instance of an image (you can start,
                stop, delete and re-create it any time)
  - VOLUME    : a folder on your real computer that is "plugged
                into" the container so data survives restarts


================================================================
 2. WHY USE DOCKER FOR THIS PROJECT (ADVANTAGES)
================================================================

  - NO PYTHON SETUP HEADACHES
    You do not need to install Python 3.11, create a venv, or
    install 20 packages on your laptop. Docker does it all inside
    the image. Anyone with Docker installed can run the project.

  - WORKS THE SAME EVERYWHERE
    The container behaves identically on Windows, macOS, Linux,
    a colleague's machine, and a cloud server. "Works on my
    machine" stops being a problem.

  - SYSTEM TOOLS ARE INCLUDED
    The image already contains git, doxygen, graphviz, node and
    eslint. You do not have to install these yourself.

  - ISOLATION AND SAFETY
    The app runs in its own sandbox. If something breaks, you
    delete the container and start fresh in seconds. Your real
    machine stays clean.

  - EASY TO SHARE AND DEPLOY
    You can push the image to a registry (Docker Hub, AWS ECR,
    etc.) and run it on any server with one command.

  - REPRODUCIBLE BUILDS
    Two months from now, the same Dockerfile gives the same
    environment. No more "what version of pandas did I have?"

  - QUICK ROLLBACK
    Old image still on your disk? Run that one. Done.


================================================================
 3. THE THREE FILES THAT MAKE THIS WORK
================================================================

In the project root you will find:

  Dockerfile         The recipe. Tells Docker how to build the
                     image: which base OS, which system packages,
                     which Python packages, which command to run.

  .dockerignore      A list of folders/files that Docker should
                     NOT copy into the image (your venv, .git,
                     local data, secrets, etc.). Keeps the image
                     small and avoids leaking secrets.

  docker_start.bat   A Windows convenience script that builds the
                     image and starts the container with all the
                     right options (port, env file, volumes).

You can read each of them - they are short and commented.


================================================================
 4. BUILD AND START THE CONTAINER (THE EASY WAY)
================================================================

Prerequisites:

  - Install Docker Desktop from https://www.docker.com/products/docker-desktop
  - Start Docker Desktop and wait until the whale icon is steady
  - Make sure you have a .env file in the project root with your
    AWS Bedrock credentials (copy .env.example to .env if needed)

Then just double-click:

    docker_start.bat

That script will:

  1. Check Docker is running
  2. Make sure .env exists
  3. Create data\ and Reports\ folders if missing
  4. Remove any old "aicm" container
  5. Build the image (first time takes a few minutes)
  6. Free port 8501 if something else is using it
  7. Start the container in the background
  8. Show you the live logs

When you see "You can now view your Streamlit app", open:

    http://localhost:8501

To stop watching the logs, press Ctrl+C. The container keeps
running in the background.

To stop the container itself:

    docker stop aicm


================================================================
 5. WHAT ACTUALLY HAPPENS WHEN THE CONTAINER STARTS
================================================================

When you run "docker run ...", Docker does this:

  1. Takes the image "ai-code-maniac" off your disk.
  2. Creates a fresh container from it (think: a new virtual
     mini-computer).
  3. Maps host port 8501 to container port 8501. That means when
     your browser visits localhost:8501 on your real machine,
     the request is forwarded into the container.
  4. Loads environment variables from .env (AWS keys, model id,
     etc.) into the container.
  5. Mounts your host data\ folder into /app/data inside the
     container. Anything written to /app/data is actually
     written to your host disk and survives container deletion.
  6. Same for Reports\ - mounted to /app/Reports.
  7. Runs the command from the Dockerfile:
        streamlit run app/Home.py
  8. Streamlit listens on 0.0.0.0:8501 inside the container,
     which you reach via localhost:8501 on your machine.


================================================================
 6. I CHANGED A PYTHON FILE - HOW DO I UPDATE THE CONTAINER?
================================================================

Important fact: the image is a SNAPSHOT of your code at build
time. Editing files on your host does NOT change the running
container, because the container has its own copy baked in.

You have two options:

----------------------------------------------------------------
 OPTION A - REBUILD (production-style, cleanest)
----------------------------------------------------------------

After changing any .py file, just re-run the start script:

    docker_start.bat

It will rebuild the image (Docker is smart - it only re-runs the
steps that actually changed, so this is usually fast), then
restart the container with your new code.

If you want to do it manually:

    docker stop aicm
    docker rm aicm
    docker build -t ai-code-maniac .
    docker run -d --name aicm -p 8501:8501 --env-file .env ^
        -v "%cd%\data:/app/data" ^
        -v "%cd%\Reports:/app/Reports" ^
        ai-code-maniac

When to use Option A:
  - You changed requirements.txt (new Python packages)
  - You changed the Dockerfile itself
  - You are preparing to deploy / share the image
  - You want a guaranteed clean state

----------------------------------------------------------------
 OPTION B - LIVE MOUNT (development, instant updates)
----------------------------------------------------------------

For active development, mount your project folder INTO the
container so the container reads your files live. Then you only
have to restart Streamlit (or rely on its auto-reload), no
rebuild needed.

Stop and remove the old container, then run:

    docker run -d --name aicm -p 8501:8501 --env-file .env ^
        -v "%cd%:/app" ^
        -v "%cd%\data:/app/data" ^
        -v "%cd%\Reports:/app/Reports" ^
        ai-code-maniac

The "-v %cd%:/app" line replaces the image's /app contents with
your current host folder. Edit a .py file, Streamlit auto-reloads
in the browser. No rebuild.

When to use Option B:
  - You are actively coding and want fast iteration
  - You are not changing requirements.txt

When NOT to use Option B:
  - For sharing or deploying (use Option A)
  - If you changed dependencies (you must rebuild)


================================================================
 7. MOUNTING A FOLDER SO THE CONTAINER CAN READ YOUR DATA
================================================================

A "volume mount" is the bridge between a folder on your real
machine (the host) and a folder inside the container.

Syntax (Windows cmd):

    -v "<host_path>:<container_path>"

Example - you have a folder C:\my_code that you want analysed:

    docker run -d --name aicm -p 8501:8501 --env-file .env ^
        -v "%cd%\data:/app/data" ^
        -v "%cd%\Reports:/app/Reports" ^
        -v "C:\my_code:/workspace/my_code" ^
        ai-code-maniac

Now inside the container, the path /workspace/my_code contains
exactly what C:\my_code holds on your laptop. In the Streamlit
UI, when you pick "Local File" as the source, type:

    /workspace/my_code

(or a file path under it). The agents will read those files.

Things to remember:

  - The container path can be anything. /workspace, /data,
    /input, etc. Pick something readable.
  - On Windows use backslashes for the host part and forward
    slashes for the container part.
  - Use "%cd%" in cmd to mean "the current folder".
  - You can mount as many folders as you want - just add more
    -v flags.
  - To make the mount read-only (safer for source data), append
    ":ro" to the container path:
        -v "C:\my_code:/workspace/my_code:ro"

Example - mounting multiple folders:

    docker run -d --name aicm -p 8501:8501 --env-file .env ^
        -v "%cd%\data:/app/data" ^
        -v "%cd%\Reports:/app/Reports" ^
        -v "C:\projects\frontend:/workspace/frontend:ro" ^
        -v "C:\projects\backend:/workspace/backend:ro" ^
        -v "D:\datasets:/datasets:ro" ^
        ai-code-maniac

Inside the UI, refer to files as /workspace/frontend/...,
/workspace/backend/..., /datasets/....


================================================================
 8. MOUNTING A FOLDER FOR LIVE DEVELOPMENT (NO REBUILD NEEDED)
================================================================

This is just Option B from section 6, repeated here because it is
worth its own callout:

    docker run -d --name aicm -p 8501:8501 --env-file .env ^
        -v "%cd%:/app" ^
        ai-code-maniac

What this does:
  - "%cd%" is your current folder (the project root)
  - ":/app" is where the project lives inside the container
  - Together: the container reads your live source files

Edit a Python file in VS Code, save it, refresh the browser -
your change is live. No rebuild, no restart needed for most
edits (Streamlit auto-reloads on file change).

If Streamlit does not auto-reload, restart just the container
without rebuilding:

    docker restart aicm


================================================================
 9. COMMON DOCKER COMMANDS YOU WILL USE EVERY DAY
================================================================

  docker ps                       List running containers
  docker ps -a                    List all containers (incl. stopped)
  docker images                   List images on your machine
  docker logs aicm                Show container logs (full)
  docker logs -f aicm             Follow logs live (Ctrl+C to detach)
  docker stop aicm                Gracefully stop the container
  docker start aicm               Start a stopped container
  docker restart aicm             Stop + start
  docker rm aicm                  Delete a stopped container
  docker rm -f aicm               Force-delete (running or not)
  docker exec -it aicm bash       Open a shell INSIDE the container
                                  (great for debugging - you can
                                  run "ls", "cat", "python ...")
  docker build -t ai-code-maniac .   Rebuild the image
  docker rmi ai-code-maniac       Delete the image
  docker system df                See how much disk Docker uses
  docker system prune             Reclaim space (deletes stopped
                                  containers and unused images)


================================================================
 10. TROUBLESHOOTING CHECKLIST
================================================================

PROBLEM: "Cannot connect to Docker daemon"
  - Open Docker Desktop and wait until it says "Engine running".

PROBLEM: "Port is already allocated"
  - Something else uses port 8501. Either stop it, or change the
    host port: -p 8600:8501  (then visit localhost:8600).

PROBLEM: My code change is not visible in the browser.
  - You probably did not rebuild. Run docker_start.bat again, or
    use the live-mount option (section 8).

PROBLEM: AWS Bedrock "Access Denied" / "Could not load credentials"
  - .env is missing or has wrong keys. Check .env in the project
    root has valid AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and
    AWS_REGION. Then restart: docker restart aicm.

PROBLEM: My data\ folder is empty inside the container.
  - You forgot to mount it. Ensure -v "%cd%\data:/app/data" is
    in your docker run command.

PROBLEM: "No such file or directory" when picking a local file
  - Inside the container, use the CONTAINER path, not the host
    path. If you mounted "C:\my_code:/workspace/my_code", the
    file inside is /workspace/my_code/some_file.py.

PROBLEM: Image build is very slow
  - First build downloads everything (several hundred MB). Later
    builds are fast because Docker caches layers. Avoid editing
    requirements.txt unnecessarily - that invalidates the cache.

PROBLEM: I want to see what is happening inside the container.
  - docker exec -it aicm bash
  - Then: ls /app, cat /app/data/arena.db (binary), python --version


================================================================
 11. CLEANING UP
================================================================

Stop and remove the container:

    docker rm -f aicm

Remove the image:

    docker rmi ai-code-maniac

Reclaim ALL unused Docker disk space (safe - only removes
stopped containers and dangling images):

    docker system prune

Aggressively reclaim space (also removes unused images and
volumes - be sure you do not need them):

    docker system prune -a --volumes


================================================================
 SUMMARY
================================================================

  - Docker packages this project + all its tools into one image.
  - Run docker_start.bat to build and launch.
  - Visit http://localhost:8501 in your browser.
  - Changed code? Re-run docker_start.bat (rebuild) OR use the
    live-mount option for instant updates during development.
  - Mount any host folder with -v "C:\path:/container/path" so
    the agents can read your code or data.
  - data\ and Reports\ on your host are already auto-mounted, so
    your DuckDB and generated reports survive container restarts.

Happy analysing!

----------------------------------------------------------------
 Author: B.Vignesh Kumar (Bravetux) - ic19939@gmail.com
 License: GNU General Public License v3 (see LICENSE)
----------------------------------------------------------------

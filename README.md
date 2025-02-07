# github-slurp
Python Script to scrape Issues &amp; PRs from a github repo using github API via `PyGithub` library. Requires Python 3.x

## Features
1.Fetches all issues from the specified repository.

2.Collects comments and comment threads.
Retrieves issue metadata: 
 title
 author
 creation date
 status
 assignees
 comments
 closed date
 closed by

3.Extracts labels and events associated with each issue.

## Setup

**Install Dependencies**
```
python3 -m pip install -r requirements.txt
```
**Generate Github Personal Access Token**

edit the ```slurp/secrets_template.py``` file
enter your github token
save file as ```slurp/secrets.py``` 
or, pass as an argument while running script (see below)

**Running the Script**
```
python3 gitslurp.py --repo=<your repository> --token=<your github PAT>
```

import argparse
from github import Auth, Github
from slurp.secrets import GITHUB_TOKEN # edit secrets_template, and save-as secrets
from slurp.issues import slurp_issues

if __name__ == "__main__":

    # setup, params
    parser = argparse.ArgumentParser(prog='github-scrape')
    parser.add_argument('--repo', help='repository to scrape from', default='tensorflow/tensorflow')
    parser.add_argument('--token', help='your github personal access token', default=GITHUB_TOKEN)
    args = parser.parse_args()

    # Authorise the github API
    auth = Auth.Token(args.token)
    g = Github(auth=auth, per_page=100)

    repo = g.get_repo(args.repo)
    print(f'* * *  {repo.name}  * * *')

    # slurp the issues and PR - all states
    slurp_issues(repo, g, num=80000, state='all')

    # and we're done
    g.close()

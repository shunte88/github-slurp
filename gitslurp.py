import argparse
from slurp.secrets import GITHUB_TOKEN # edit secrets_template, and save-as secrets
from slurp.issues import GitHub

if __name__ == "__main__":

    # setup, params
    parser = argparse.ArgumentParser(prog='github-scrape')
    # namespace / repo, maybe split these amd make repo delimited list??
    parser.add_argument('--repo', help='repository to scrape from', default='pytorch/pytorch')
    parser.add_argument('--issues', type=int, help='number of issues to retrieve', default=80000)
    parser.add_argument('--token', help='your github personal access token', default=GITHUB_TOKEN)
    args = parser.parse_args()

    # slurp the issues and PR - all states
    GitHub(pat=args.token,repo=args.repo, issue_max=args.issues).slurp_issues()

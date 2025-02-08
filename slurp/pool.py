# Updated round-robin token rotation mechanism
from github import Auth, Github
from github import GithubException, BadCredentialsException
from secrets import GITHUB_TOKEN

class GitHubTokenPool:
    """
    Manages a pool of GitHub tokens using a round-robin approach.
    """

    def __init__(self, tokens):
        self.tokens = tokens
        self.index = 0  # Start from the first token

    def get_next_client(self):
        """
        Returns the next available GitHub client in a round-robin manner.
        """
        for _ in range(len(self.tokens)):  # Ensure we don't loop indefinitely
            token = self.tokens[self.index]
            self.index = (self.index + 1) % len(self.tokens)  # Move to the next token

            try:
                client = Github(token)
                rate_limit = client.get_rate_limit()
                print(rate_limit.core.remaining)
                if rate_limit.core.remaining > 100:  # Ensure token has enough remaining calls
                    return client

            except Exception as e:
                print(f"Token failed: {token[:10]}... | Error: {str(e)}")

        print("All tokens exhausted. Sleeping until reset...")
        time.sleep(3600)  # Wait an hour for limits to reset before retrying
        return self.get_next_client()  # Retry after sleep

# Initialize the token pool with round-robin logic
token_pool = GitHubTokenPool(GITHUB_TOKEN)

# Function to fetch GitHub issues using round-robin token rotation
def fetch_github_issues(repo_name, max_issues=500):
    """Fetches issues from a GitHub repo using round-robin token rotation."""
    client = token_pool.get_next_client()
    repo = client.get_repo(repo_name)
    issues = []

    try:
        for issue in repo.get_issues(state="all"):
            issues.append(issue)
            print(f'issues: {len(issues)}')
            if len(issues) >= max_issues:
                break
    except RateLimitExceededException:
        print("Rate limit exceeded, switching tokens...")
        return fetch_github_issues(repo_name, max_issues - len(issues))  # Continue fetching with new token

    return issues

# Example usage
repo_name = "tensorflow/tensorflow"  # Replace with target repo
print(repo_name)
issues = fetch_github_issues(repo_name, max_issues=9000)
print(f"Fetched {len(issues)} issues from {repo_name}.")

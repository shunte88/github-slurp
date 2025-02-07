import time
import os
import logging
import pandas as pd
from github import Auth, Github
from github import GithubException, BadCredentialsException
from .secrets import GITHUB_TOKEN # edit secrets_template, and save-as secrets


class GitHub():
    def __init__(self, pat=GITHUB_TOKEN, per_page=100, issue_max=100, repo=None):
        # Authorise the github API
        self.per_page = per_page
        self.issue_max=issue_max
        self.base = './data'
        if type(pat) is list:
            self.pat_round_robin = True
            self.pat_index = 0
            self.pat_list = pat
        elif type(pat) is str:
            self.pat = pat
            self.pat_list = []
            self.pat_index = 0
            self.pat_round_robin = False
        else:
            logging.error(f'Invalid GitHub token entered, authentication failed.')
            raise ValueError('Invalid GitHub token entered, authentication failed.')
        self._next_pat()
        if self.gh and repo:
            self.repo = self.gh.get_repo(repo)
            logging.debug(f'* * *  {self.repo.name}  * * *')
            self.base = self.repo.full_name.replace('/', '_')
            self.base = os.path.join('./data', self.base)
            self._init_base()

    def __enter__(self):
        return self
    
    def __exit__(self):
        self.gh.close()
        return

    def _next_pat(self):
        if self.pat_round_robin:
            self.pat = self.pat_list[self.pat_index]
            self.pat_index = (self.pat_index + 1) % len(self.pat_list)
        # [re]connect to the API
        self.gh = self._connect()
        '''
        if self.rate_limit < 100:
            logging.warning(f'Rate limit is {rate_limit}, consider adding more tokens to the pool.')
            self.gh.close()
            self._next_pat(
        '''

    def _connect(self):
        auth = Auth.Token(self.pat)
        gh = Github(auth=auth, per_page=self.per_page)
        try:
            gh.get_user().login
            self.rate_limit = gh.get_rate_limit()
            return gh
        except GithubException as e:
            logging.warning(f'No valid GitHub token entered, authentication failed: {e}.')
        except BadCredentialsException as e:
            logging.warning(f'GitHub User authentication failed: {e}.')
        return None


    def _remove_quoted_comments(self, text):
        """
        Remove quoted comments in replies
        """
        lines = text.splitlines()
        useful_lines = [line for line in lines if not line.strip().startswith('>')]

        return "\n".join(useful_lines).strip()

    def _process_comment(self, comment_list, issue_id, issue_creator, issue_assignees):
        """
        Processes each comment to be more readable
        """
        comments = []
        comment_thread = ''

        for comment in comment_list:
            # if comment.user.login == 'google-ml-butler[bot]': # only comments feedback URLs, skip
            #     continue
            
            # Add possibly helpful role of authors in the thread
            author = comment.user.login
            if author == issue_creator:
                author += " (Issue Creator)"

            elif author in issue_assignees:
                author += " (Assginee)"

            date = comment.created_at.strftime("%Y-%m-%d %H:%M:%S %Z")
            # convert instances of'> {prev_comment} \n {current comment}' to '{current comment}'
            body = self._remove_quoted_comments(comment.body) 

            comment_thread += f'{author} on ({date}): {body}' +'\n\n'
            comments.append(
                {
                    'comment_id':comment.id, 
                    "issue_id":issue_id, 
                    "author":comment.user.login,
                    "body":comment.body.strip(),
                    "created_at":comment.created_at
                    })
        return comments, comment_thread

    def _fetch_issue(self, issue):
        """
        Processes data for a single issue and returns it in a dictionary
        """
        issue_type = 'pull_request' if issue.pull_request else 'issue'
        
        assignee_list = [user.login for user in issue.assignees]
        comments, comment_thread = self._process_comment(issue.get_comments(), issue.id, issue.user.login, assignee_list)
        labels = issue.labels
        
        return  {
                "id": issue.id,
                "type": issue_type,
                "state": issue.state,
                "state_reason": issue.state_reason,
                "title": issue.title,
                "body": issue.body,
                "author": issue.user.login,
                "created_at": issue.created_at,
                "assignees": assignee_list,
                "updated_at": issue.updated_at,
                #"updated_by": issue.user.updated_by,
                "closed_at": issue.closed_at,
                #"closed_by": issue.user.closed_by,
                "url": issue.html_url,
                "labels": [(label.name, label.description) for label in labels],
                "comments_list": comments,
                "comment_thread":comment_thread
            }

    def _init_base(self):
        """
        Initialize base data folder and define output entities
        """
        os.makedirs(self.base, exist_ok=True)  # Ensure the directory exists
        # and define our files
        self.last_page_file = os.path.join(self.base, 'last_page.txt')
        self.issues_file = os.path.join(self.base, f'{self.repo.name}_issues.csv'.strip())
        self.pull_requests_file = os.path.join(self.base, f'{self.repo.name}_pull_requests.csv'.strip())

    def _load_progress(self):
        """
        Load progress from previosuly saved files to resume from
        """
        self._page_num = 0
        if os.path.exists(self.last_page_file):
            with open(self.last_page_file, 'r') as f:
                self._page_num = int(f.read().strip())

        logging.info(f'Loading progress, starting from page {self._page_num}')
        return self._page_num

    def _save_progress(self, new_issues, new_pull_requests):
        """
        Saves the data fetched after processing every page and updates the page number to resume from in case of failure
        """
        if new_issues:
            df_issues = pd.DataFrame(new_issues)
            file_exists = os.path.exists(self.issues_file)
            df_issues.to_csv(self.issues_file, mode='a', header= (not file_exists), index=False)
        
        if new_pull_requests:
            df_pull_requests = pd.DataFrame(new_pull_requests)
            file_exists = os.path.exists(self.pull_requests_file)
            df_pull_requests.to_csv(self.pull_requests_file, mode='a', header= (not file_exists), index=False)
        
        with open(self.last_page_file, 'w') as f: # update the page to resume from
            f.write(str(self._page_num))

        logging.info(f'Progress saved at {self._count} records... we\'ll resume from page {self._page_num}')


    # should we add data cleanup here?
    def slurp_issues(self, state='all'):
        """
        Scrapes all Issues from the given repository and stores data to a DataFrame
        """
        
        self._page_num = self._load_progress() # load past progress
        self._count = self._page_num * self.per_page # if per page is 100 so total fetched is 0*100, 1*100, etc.

        while self._count < self.issue_max:
            try:
                issue_page = self.repo.get_issues(state=state).get_page(self._page_num)
                if not issue_page:
                    return
                new_issues = []
                new_pull_requests = []

                for issue in issue_page:
                    if self._count >= self.issue_max:
                        break
                    result = self._fetch_issue(issue)
                    if result['type'] == 'pull_request':
                        new_pull_requests.append(result)
                    else:
                        new_issues.append(result)
                    
                    self._count += 1
                self._page_num += 1
                self._save_progress(new_issues, new_pull_requests)

            except GithubException as e:
                logging.error(f'Encountered Github Exception {e.status} {e.message} {e.headers}')
                self._save_progress([], [])
                if e.status == 403 and self.gh is not None:
                    if self.pat_round_robin:
                        self._next_pat()    
                        logging.info(f'Rotate on token pool')
                    else:
                        reset_time = self.gh.rate_limiting_resettime
                        wait_time = max(reset_time - time.time(), 60*10)
                        logging.info(f'Rate limit, sleeping for {wait_time} seconds')
                        time.sleep(wait_time) # sleep
                    continue
                else:
                    logging.error(f'Unsuporrted error {e}')
                    raise e # some other error


        return 
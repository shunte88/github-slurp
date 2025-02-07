import time
import os
import pandas as pd
from github import GithubException


def remove_quoted_comments(text):
    """
    Remove quoted comments in replies
    """
    lines = text.splitlines()
    useful_lines = [line for line in lines if not line.strip().startswith('>')]

    return "\n".join(useful_lines).strip()

def process_comment(comment_list, issue_id, issue_creator, issue_assignees):
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
        body = remove_quoted_comments(comment.body) 

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

def fetch_issue(issue):
    """
    Processes data for a single issue and returns it in a dictionary
    """
    issue_type = 'pull_request' if issue.pull_request else 'issue'
    
    assignee_list = [user.login for user in issue.assignees]
    comments, comment_thread = process_comment(issue.get_comments(), issue.id, issue.user.login, assignee_list)
    labels = issue.labels
    
    return  {
            "id": issue.id,
            "type": issue_type,
            "title": issue.title,
            "body": issue.body,
            "author": issue.user.login,
            # "assignees":issue.assignees,
            "created_at": issue.created_at,
            "closed_at": issue.closed_at,
            "url": issue.html_url,
            "labels": [(label.name, label.description) for label in labels],
            "comments_list": comments,
            "comment_thread":comment_thread
        }

def load_progress(base='./data'):
    """
    Load progress from previosuly saved files to resume from
    """

    page_num = 0
    os.makedirs(base, exist_ok=True)  # Ensure the directory exists
    last_page_file = os.path.join(base, 'last_page.txt')
    if os.path.exists(last_page_file):
        with open(last_page_file, 'r') as f:
            page_num = int(f.read().strip())

    print(f'Loading progress, starting from page {page_num}')
    return page_num

def save_progress(new_issues, new_pull_requests, page_num, base='./data', count=0):
    """
    Saves the data fetched after processing every page and updates the page number to resume from in case of failure
    """
    os.makedirs(base, exist_ok=True)
    issues_file = os.path.join(base, 'scraped_issues.csv')
    pull_requests_file = os.path.join(base, 'scraped_pull_requests.csv')
    if new_issues:
        df_issues = pd.DataFrame(new_issues)
        file_exists = os.path.exists(issues_file)
        df_issues.to_csv(issues_file, mode='a', header= (not file_exists), index=False)
    
    if new_pull_requests:
        df_pull_requests = pd.DataFrame(new_pull_requests)
        file_exists = os.path.exists(pull_requests_file)
        df_pull_requests.to_csv(pull_requests_file, mode='a', header= (not file_exists), index=False)
    
    with open(os.path.join(base,'last_page.txt'), 'w') as f: # update the page to resume from
        f.write(str(page_num))

    print(f'Progress saved at {count} records... we\'ll resume from page {page_num}')


# should we add data cleanup here?
def scrape_issues(repo, g, num=100, state='closed'):
    """
    Scrapes closed Issues from the given repository and stores data in a DataFrame
    """
    
    base = repo.full_name.replace('/', '_')
    base = os.path.join('./data', base)
    page_num = load_progress(base) # load previous progress
    count = page_num * 100 # per page is 100 so total fetched is 0*100, 1*100, etc.

    while count < num:
        try:
            issue_page = repo.get_issues(state=state).get_page(page_num)
            if not issue_page:
                return
            new_issues = []
            new_pull_requests = []

            for issue in issue_page:
                if count >= num:
                    break
                result = fetch_issue(issue)
                if result['type'] == 'pull_request':
                    new_pull_requests.append(result)
                else:
                    new_issues.append(result)
                
                count += 1
            page_num += 1
            save_progress(new_issues, new_pull_requests, page_num, base=base, count=count)

        except GithubException as e:
            print(f'Encountered Github Exception {e.status} {e.message} {e.headers}')
            save_progress([], [], page_num)
            if e.status == 403 and g is not None:
                reset_time = g.rate_limiting_resettime
                wait_time = max(reset_time - time.time(), 60*10)
                print(f'Rate limit reached...Sleeping for {wait_time} seconds')
                time.sleep(wait_time) # sleep for a minimum of 10 minutes
                continue
            else:
                print('Some other error...')
                raise e # some other error


    return 
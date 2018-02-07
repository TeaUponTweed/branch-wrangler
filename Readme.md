Git Issues:
- asking Nick lots of questions
- rebasing every time a mainline branch moves forward
- multiple people changing the same code
- unmanaged branches
- testing
- enforcing JIRA (git) standards: branch names, commit message standards, test standards
- getting code reviews
- nasty rebases
- people being selfish with cloud resources

Ideas:
- need to maintain a high signal to noise ratio
- make Nick's job easier
- public shaming for lack of testing
- stats (lines removed, commits)
- mattermost bot that makes jira tickets

Names:
- branch cowboy: wrangling git branches since 2018
- tigger: your eager git assistant

Projects:
- mattermost jira ticket maker bot
- automatic git branch rebasing bot
- public shaming of untested pushed code

--------------------
Actions:
- setup branch chain: gbw add --name chain branch1 branch2 [...]
  * let user know if breaks previous chain (fail)
- list active chains: gbw list
- upon link moving forward, message rider about whether clean rebase
  * if clean, ask permission to perform rebases
  * if not clean, just make it clear
- break link: gbw rm branch (removes link)
- break chain: gbw rm chain (removes chain/breaks all links)
- reorder: give same set of commits but with a different order
- update: merge detection (updates chain if some branches have been merged)
- help: gbw help


- requirement: a branch can only have one thing its chained to

Commands:




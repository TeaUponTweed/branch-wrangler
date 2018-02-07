import subprocess, sys

from typing import List, Dict, NamedTuple, Callable, Optional, Tuple, Iterable


class Branch(NamedTuple):
    name: str
    sha: str

def git_call(cmd: str) -> str:
    completed = subprocess.run('git {}'.format(
        cmd).split(), check=True, stdout=subprocess.PIPE)
    return completed.stdout

Chain = List[Branch]

class Wrangler(object):
    def __init__(self):
        self.chains = {}
        self.chainnum = 0

    def status(self):
        '''
        states:
        * valid
        * fast forwardable
        * not fast forwardable
        * partially merged
        * invalid (missing links)
        '''
        pass

    def add_chain(self, branch_names, chain_name=None):
        all_branches = set(git_call('branch -r').split())
        print(all_branches)
    
    def list_chains(self):
        pass

    def remove_link(self, branch_names):
        pass

    def remove_chain(self, chain_name):
        pass
    
    def reorder_chain(self, branch_names):
        pass

    def fetch(self):
        pass

    def fast_forward_chain(self, chain):
        '''
        rebase chain
        '''
        pass
    
    def handle_merges(self, chain):
        pass


def main():
    w = Wrangler()
    command = sys.argv[1]
    command = getattr(w, command)
    # import ipdb; ipdb.set_trace()
    # assert command in w.__dict__
    command(w, sys.argv[2:])

if __name__ == '__main__':
    main()

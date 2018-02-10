#!/usr/bin/env python

import pickle
import hashlib
import subprocess
import sys
import os
import time
import fire
import itertools as it
from typing import List, NamedTuple, Set


Hash = str
BranchName = str
ChainName = str

class Branch(NamedTuple):
    name: BranchName
    sha: Hash

Chain = List[Branch]


def git_call(*cmd: List[str], **subprocess_args) -> str:
    cmd = ' '.join(cmd)
    completed = subprocess.run('git {}'.format(
        cmd).split(), check=True, stdout=subprocess.PIPE, **subprocess_args)
    return completed.stdout.decode("utf-8").replace('"', '').rstrip()


def get_all_remote_branch_names() -> Set[BranchName]:
    return set(git_call('branch --remotes --format="%(refname:lstrip=2)').split())


def get_all_remote_branches() -> Set[Branch]:
    # return set(Branch(b, get_hash(b)) for b in get_all_remote_branch_names())
    return set(make_chain(get_all_remote_branch_names()))


def get_hash(branch) -> Hash:
    return git_call('rev-parse', branch)


def get_remotes() -> Set[str]:
    return set(git_call('remote').split())


def make_chain(branch_names) -> Chain:
    return [Branch(b, get_hash(b)) for b in branch_names]


def get_chain_name(branch_names) -> ChainName:
    return hashlib.sha256(
    ' '.join(branch_names).encode("utf-8")).hexdigest()

def FATAL(msg):
    print(msg, file=sys.stderr)
    exit(1)


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = it.tee(iterable)
    next(b, None)
    return zip(a, b)


_VERBOSE = True
_REALLY_VERBOSE = True
def DEBUG(msg):
    if _VERBOSE:
        print(msg, file=sys.stderr)


def DEBUG2(msg):
    if _REALLY_VERBOSE:
        print(msg, file=sys.stderr)



def ERROR(msg):
    print(msg, file=sys.stderr)


def LOG(msg):
    print(msg, file=sys.stderr)

Chain = List[Branch]

def _is_remote_specified(branch: BranchName) -> bool:
    remotes = get_remotes()
    retmote_name = branch.split('/')[0]
    return retmote_name in remotes


class Wrangler(object):
    def __init__(self):
        self.git_dir = git_call('rev-parse --show-toplevel')
        self.wrangler_dir = os.path.join(self.git_dir, '.wrangler')
        os.makedirs(self.wrangler_dir, exist_ok=True)
        self.wrangler_lock_file = os.path.join(self.wrangler_dir, 'LOCK')
        self.wrangler_object_file = os.path.join(self.wrangler_dir, 'wrangler.pkl')
        self.start_time = time.time()
        self.default_remote = 'origin'
        if os.path.exists(self.wrangler_lock_file):
            FATAL('The wrangler data base is locked. If this is in error, '
                'manually delete the LOCK file in the .wrangler directory')
        else:
            with open(self.wrangler_lock_file, 'w') as lock:
                lock.write('{}\n'.format(time))

        if os.path.exists(self.wrangler_object_file):
            with open(self.wrangler_object_file, 'rb') as f:
                try:
                    old_wrangler = pickle.load(f)
                except pickle.UnpicklingError:
                    print('WARNING: failed to load wrangler object database. Starting over.')
                    self.chains = {}
                else:
                    self.chains = old_wrangler.chains
        else:
            self.chains = {}

        # TODO calculate unambiguous_chain_name_length dynamically
        self.unambiguous_chain_name_length = 8

    def set_default_remote(self, remote_name: str):
        all_remotes = get_remotes()
        if remote_name not in all_remotes:
            FATAL('Unknown remote {}'.format(remote_name))

        if self.default_remote is None:
            LOG('Setting default remote to {}'.format(remote_name))
        else:
            LOG('Changing default remote from {} to {}'.format(self.default_remote, remote_name))

        self.default_remote = remote_name

    def _display_chainname(self, chainame: ChainName) -> ChainName:
        return chainame[:self.unambiguous_chain_name_length]

    def update(self, dryrun=False):
        all_up_to_date = True
        all_branches = get_all_remote_branches()
        for chainname, branches in self.chains.items():
            for ix, branch in enumerate(branches):
                if branch in all_branches:
                    continue
                all_up_to_date = False
                remote_branch = [b for b in all_branches if b.name == branch.name]
                if len(remote_branch) == 0:
                    ERROR('Can\t update unknown branch {}'.format(branch.name))
                    continue
                if len(remote_branch) > 1:
                    FATAL('Multiple remote branches with name {}'.format(branch.name))
                if dryrun:
                    print('Would update {} to {}'.format(branch.name, remote_branch[0].sha))
                else:
                    LOG('Updating {}'.format(branch.name))
                    self.chains[chainname][ix] = Branch(branch.name, remote_branch[0].sha)
        if all_up_to_date:
            print('All up-to-date')

    def status(self) -> None: # CONST
        all_branches = get_all_remote_branches()
        for branches in self.chains.values():
            up_to_date = True
            print('[ {} ]'.format(' <- '.join(b.name for b in branches)))
            for branch in branches:
                # Check if all branches chain still in remote
                if branch.name not in (b.name for b in all_branches):
                    print('{} no longer in remotes. Was it merged?'.format(branch.name))
                    up_to_date = False
                elif branch not in all_branches:
                    print('{} has moved'.format(branch.name))
                    up_to_date = False

            if not up_to_date:
                ERROR('\n Branch wrangler out-of-sync. Run update command\n')
                continue

            # Check if chain can apply cleanly
            rebaseable = True
            try:
                git_call('diff --quiet')
            except subprocess.CalledProcessError:
                wd_dirty = True
            else:
                wd_dirty = False

            if wd_dirty:
                git_call('stash')

            try:
                current_branch_name = git_call('rev-parse --abbrev-ref HEAD')
                if current_branch_name == 'tmp/cowboy-rebase-start':
                    FATAL('Currently on wrangler reserved branch. We are in a weird state and will now exit')
                # go to temporary branch
                try:
                    git_call('branch -D tmp/cowboy-rebase-start')
                except subprocess.CalledProcessError:
                    pass
                git_call('checkout -b tmp/cowboy-rebase-start')
                # attempt to rebase
                sys.stdout.write('[ {}'.format(branches[0].name))
                for current_branch, next_branch in pairwise(branches):
                    try:
                        git_call('rebase --onto', current_branch.name,
                                 next_branch.name, stderr=subprocess.DEVNULL)
                    except subprocess.CalledProcessError:
                        # ERROR("Cant rebase {} onto {}".format(current_branch.name, next_branch.name))
                        sys.stdout.write(' XX ')
                        git_call('rebase --abort', stderr=subprocess.DEVNULL)
                        rebaseable = False
                    else:
                        sys.stdout.write(' <- ')
                    sys.stdout.write(next_branch.name)
                print(' ]')
            finally:
                git_call('checkout', current_branch_name,
                         stderr=subprocess.DEVNULL)
                git_call('reset HEAD --hard')
                if wd_dirty:
                    git_call('stash pop')

            if not rebaseable:
                FATAL('Chain does not rebase cleanly')

    def _prepend_remote_to_branch_name(self, branch: BranchName) -> BranchName:
        if _is_remote_specified(branch):
            return branch
        elif self.default_remote is None:
            FATAL('Specify remote for {} or set default remote'.format(branch))
        else:
            return '{}/{}'.format(self.default_remote, branch)

    def handle_merges(self, dryrun: bool = False):
        pass

    def add_chain(self, *branch_names: List[BranchName]):
        branch_names = list(map(self._prepend_remote_to_branch_name, branch_names))
        if len(branch_names) <= 1:
            FATAL('Need at least two branches to make a chain')

        all_branches = get_all_remote_branch_names()
        # check that branch names are valid
        unknown_branches = set(branch_names) - all_branches
        if unknown_branches:
            for branch in unknown_branches:
                if not _is_remote_specified(branch):
                    ERROR('Need to specify remote for {} for set default remote'.format(branch))
                else:
                    ERROR('Unknown branch {}'.format(branch))

            FATAL('branch(es) [ {} ] not in remote refs'.format(
                  ' '.join(sorted(unknown_branches))))
        # check that branches not already tracked
        no_branches_already_chained = True

        for chainname, branches in self.chains.items():
            already_tracked_branches = set(branch_names) & set(b.name for b in branches)
            if already_tracked_branches:
                FATAL('branch(es) {} already tracked in chain {}'.format(
                    ' '.join(already_tracked_branches), self._display_chainname(chainname)))
                no_branches_already_chained = False

        if not no_branches_already_chained:
            FATAL('Not adding chain')

        # add chain
        chainname = get_chain_name(branch_names)

        if chainname in self.chains:
            FATAL('Wow! you won the lottery and got a hash collision!')

        self.chains[chainname] = make_chain(branch_names)#[Branch(branch_name, get_hash(branch_name)) for branch_name in branch_names]

    def list_chains(self) -> None: # CONST
        # TODO shorter (still unique hash length)
        for name, branches in self.chains.items():
            print('{}: [ {} ]'.format(self._display_chainname(name), ' <- '.join(b.name for b in branches)))

    def remove_link(self, *branch_names_to_remove: List[str], dryrun: bool = False, _first_call: bool=True):
        branch_names_to_remove = set(
            map(self._prepend_remote_to_branch_name, branch_names_to_remove))

        if not branch_names_to_remove and _first_call: 
            FATAL('No links to remove specified')

        for branch_name_to_remove in branch_names_to_remove:
            for chainname, branches in list(self.chains.items()):
                full_chainname = chainname
                chainname = self._display_chainname(chainname)
                if branch_name_to_remove in (b.name for b in branches):
                    if dryrun:
                        LOG('Would remove link {} from {}'.format(branch_name_to_remove, chainname))
                    else:
                        DEBUG('Removing link {} from chain {}'.format(branch_name_to_remove, chainname))
                        new_branch = [
                            b for b in branches if b.name != branch_name_to_remove]
                        self.chains.pop(full_chainname)
                        full_chainname = get_chain_name([b.name for b in new_branch])
                        self.chains[full_chainname] = new_branch
                    if len(self.chains[full_chainname]) < 2:
                        LOG('No longer enough links in chain. Removing chain')
                        self.chains.pop(full_chainname)

                    branch_names_to_remove.remove(branch_name_to_remove)
                    return self.remove_link(*branch_names_to_remove, dryrun=dryrun, _first_call=False)

            FATAL('Can\'t remove unknown link {}'.format(branch_name_to_remove))

    def remove_chain(self, *chainnames: List[ChainName], dryrun: bool = False) -> None:
        for chainname in chainnames:
            # TODO need sha substringiness
            valid_chains = [name for name in self.chains.keys()
                            if name.startswith(chainname)]
            if not valid_chains:
                FATAL('No chain matches {}'.format(chainname))
            if len(valid_chains) > 1:
                FATAL('chain {} is ambiguous'.format(chainname))

            if dryrun:
                print('Would remove chain {}'.format(chainname))
            else:
                self.chains.pop(*valid_chains)

    def reorder_chain(self, *branch_names: List[str]) -> None:
        branch_names = list(
            map(self._prepend_remote_to_branch_name, branch_names))
        
        for chainname, branches in list(self.chains.items()):
            full_chainname = chainname
            chainname = self._display_chainname(chainname)
            if set(branch_names) & set(b.name for b in branches):
                if set(branch_names) != set(b.name for b in branches):
                    FATAL('[ {} ] intersects with chain {} but includes different branches'.format(
                        ' <- '.join(branch_names), chainname))
                else:
                    if branch_names == [b.name for b in branches]:
                        FATAL('Same order as chain {}'.format(chainname))
                    LOG('Reordering chain [ {} ] to [ {} ]'.format(' <- '.join(b.name for b in branches), ' <- '.join(branch_names)))
                    self.chains.pop(full_chainname)
                    self.chains[get_chain_name(branch_names)] = make_chain(branch_names)
                    return

        FATAL('No chain matching [{}]'.format(' '.join(branch_names)))

    def fetch(self) -> None:
        git_call('fetch')
        self.status()

    def fast_forward_chain(self, chain):
        """
        rebase chain
        """
        pass

    def dump(self) -> None:
        '''
        Saves wrangler state to disk as a pickled object in .wrangler directort
        '''
        # TODO make wrangler more robust/sharable by checking in wrangler objects as git commits
        with open(self.wrangler_object_file, 'wb') as out:
            pickle.dump(self, file=out)
        os.remove(self.wrangler_lock_file)


def main():
    try:
        w = Wrangler()
        fire.Fire(w)
    finally:
        w.dump()


if __name__ == '__main__':
    main()

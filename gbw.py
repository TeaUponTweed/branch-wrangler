#!/usr/bin/env python

import pickle
import hashlib
import subprocess
import sys
import os
import time
import fire

from typing import List, NamedTuple


class Branch(NamedTuple):
    name: str
    sha: str


def git_call(cmd: str) -> str:
    completed = subprocess.run('git {}'.format(
        cmd).split(), check=True, stdout=subprocess.PIPE)
    return completed.stdout.decode("utf-8").replace('"', '').rstrip()


Chain = List[Branch]


class Wrangler(object):
    def __init__(self):
        self.verbose = True
        self.git_dir = git_call('rev-parse --show-toplevel')
        self.wrangler_dir = os.path.join(self.git_dir, '.wrangler')
        os.makedirs(self.wrangler_dir, exist_ok=True)
        self.wrangler_lock_file = os.path.join(self.wrangler_dir, 'LOCK')
        self.wrangler_object_file = os.path.join(self.wrangler_dir, 'wrangler.pkl')
        self.start_time = time.time()
        if os.path.exists(self.wrangler_lock_file):
            print('The wrangler data base is locked. If this is in error, '
                  'manually delete the LOCK file in the .wrangler directory',
                  file=sys.stderr)
            exit(1)
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
    def _display_chainname(self, chainame):
        # TODO calculate dynamically
        unambiguous_length = 8
        return chainame[:unambiguous_length]

    def status(self):
        all_branches = self._get_all_remote_branches()
        for chainname, branches in self.chains.items():
            up_to_date = True
            fast_forwardable = False
            def not_up_to_date(msg):
                up_to_date = False
                sys.stdout.write('\n\t' + msg)

            sys.stdout.write('{}: '.format(self._display_chainname(chainname)))
            for branch in branches:
                # Check if all branches chain still in remote
                if branch not in all_branches:
                    not_up_to_date('{} no longer in remotes. Was it merged?')
                # TODO Check if branch points have changed
                # TODO Check if any links in chain have been merged

            # TODO Check if chain can apply cleanly

            if up_to_date:
                print('Up to date')
            if not up_to_date and fast_forwardable:
                print('Fast forwardable')

        """
        states:
        * valid
        * fast forwardable
        * not fast forwardable
        * partially merged
        * invalid (missing links)
        """
    def handle_merges(self, dryrun=False):
        pass

    def _get_all_remote_branches(self):
        return set(git_call('branch --remotes --format="%(refname:lstrip=3)').split())

    def add_chain(self, *branch_names):
        if len(branch_names) <= 1:
            print('Need at least two branches to make a chain', file=sys.stderr)
            exit(1)

        all_branches = self._get_all_remote_branches()
        # check that branch names are valid
        unknown_branches = set(branch_names) - all_branches
        if unknown_branches:
            print('branch(es) [ {} ] not in remote refs'.format(
                  ' '.join(sorted(unknown_branches))), file=sys.stderr)
            exit(1)
        # check that branches not already tracked
        no_branches_already_chained = True

        for chain_name, branches in self.chains.items():
            already_tracked_branches = set(branch_names) & set(branches)
            if already_tracked_branches:
                print('branch(es) {} already tracked in chain {}'.format(
                    ' '.join(already_tracked_branches), chain_name), file=sys.stderr)
                no_branches_already_chained = False
        if not no_branches_already_chained:
            exit(1)

        # add chain
        chain_name = hashlib.sha256(
            ' '.join(branch_names).encode("utf-8")).hexdigest()
        assert chain_name not in self.chains, 'Wow! you won the lottery and got a hash collision!'
        # TODO construct branch objects with shas
        self.chains[chain_name] = list(branch_names)

    def list_chains(self):
        # TODO shorter (still unique hash length)
        for name, branches in self.chains.items():
            print('{}: {}'.format(self._display_chainname(name), '->'.join(branches)))

    def remove_link(self, *branch_names):
        if not branch_names:
            return

        branch_names = set(branch_names)
        for branch_name_to_remove in branch_names:
            for chainname, branches in list(self.chains.items()):
                if branch_name_to_remove in branches:
                    if self.verbose:
                        print('Removing branch {} from chain {}'.format(
                            branch_name_to_remove, chainname), file=sys.stderr)
                    self.chains[chainname].remove(branch_name_to_remove)
                    if len(self.chains[chainname]) < 2:
                        if self.verbose:
                            print('No more links in chain. Removing chain {}'.format(chainname), file=sys.stderr)
                        self.chains.pop(chainname)

                    branch_names.remove(branch_name_to_remove)
                    return self.remove_link(*branch_names)
            print('Can\'t remove unknown link {}'.format(branch_name_to_remove))
            exit(1)

    def remove_chain(self, *chain_names):
        for chain_name in chain_names:
            # TODO need sha substringiness
            valid_chains = [name for name in self.chains.keys()
                            if name.startswith(chain_name)]
            if not valid_chains:
                print('No chain matches {}'.format(chain_name), file=sys.stderr)
                exit(1)
            if len(valid_chains) > 1:
                print('chain {} is ambiguous'.format(chain_name), file=sys.stderr)
                exit(1)
            self.chains.pop(*valid_chains)

    def reorder_chain(self, branch_names):
        pass

    def fetch(self):
        pass

    def fast_forward_chain(self, chain):
        """
        rebase chain
        """
        pass

    def dump(self):
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

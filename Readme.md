Audience:
---------
Development teams that use a rebase and merge git workflow

Purpose:
---------
The goal of this project is to make Nick's job easier. If you don't know Nick, he/she is the
developer on your team who is in charge of rebasing all the development branches when the
mainline branch moves forward. This consumes a lot of Nick's time, and Nick's time is valuable.
Now Nick can get to fixing rebase conflicts faster.

Usage:
--------
gbw help -> get usage information
gbw fetch -> update remote branch states
gbw status -> prints whether chains rebase cleanly
gbw add branch1 branch2 ... -> create chain of remote branch rebase dependencies
gbw list -> list active chains
gbw rm branch1 ... -> remove link between specified branch and parent
gbw rm chain-sha -> remove entire chain of dependencies
gbw reorder chain-sha -> reorder rebase chain (must include all branches from chain definition)

denovo-variant-examples
=======================

Examples of running denovo-variant-caller on GCE instances


Creating GCE instances
----------------------

To get a list of all the options :
~~~
$ fab -l -f src/scripts/fabfile.py
Available commands:

    create_denovo_instances      Create new denovo instances
    delete_all_denovo_instances  Deletes all denovo instances
    delete_instance              Deletes a particular instance by name
    list_denovo_instances        Lists all the denovo instances
    list_instances               Lists all the instances in my GCE
~~~

Examples
--------

Create a new denovo instance :
    
    $ fab -f src/scripts/fabfile.py create_denovo_instances
    Creating instances...
    Creating disk denovo-1
    Creating instance denovo-1

    Done.

Create several instances with 4 cores each :

    $ fab -f src/scripts/fabfile.py create_denovo_instances:num_instances=2,num_cores=4
    Creating instances...
    Creating disk denovo-2
    Creating instance denovo-2
    Creating disk denovo-3
    Creating instance denovo-3

    Done.

List all the denovo instances :

    $ fab -f src/scripts/fabfile.py list_denovo_instances
    denovo-1
    denovo-2
    denovo-3

    Done.

Delete instance `denovo-1` : 
   
    $ fab -f src/scripts/fabfile.py delete_instance:denovo-1
    Deleting instance : denovo-1...

    Done.

Delete all denovo instances :

    $ fab -f src/scripts/fabfile.py delete_all_denovo_instances
    Deleting all denovo instances...
    Are you sure? (y|n): y
    Deleting instance : denovo-2...
    Deleting instance : denovo-3...

    Done.




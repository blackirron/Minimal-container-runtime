<b>Minimal Container Runtime</b>

A lightweight Linux container runtime built from first principles.
This project re-implements the core ideas behind Docker using Linux namespaces, cgroups v2, and a minimal root filesystem to clearly demonstrate how containers work internally.

<b>Program Lifecycle</b>


```python main.py echo hello```

        ↓
        `
```main() called```

        ↓

```run_container(["echo", "hello"]) called```

        ↓
        
```fork() splits into parent + child```

        ↓
        
child:  sets CONTAINER_INIT=1

        re-execs itself
        setup_namespaces()
        setup_cgroups()
        setup_rootfs()
        setup_mounts()
        execvp("echo", ["echo", "hello"])  ← runs your command
        "hello" gets printed
        child exits
        ↓
parent: waitpid() unblocks

        run_container() returns
        main() returns
        parent exits
        ↓
       DONE

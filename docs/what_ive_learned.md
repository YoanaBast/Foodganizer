## My Struggles and What I’ve Learned:

- 404 pages don’t render with `DEBUG=False`; WhiteNoise helps serve static files.  
- CSS `@import` works in development but breaks after `collectstatic` + `DEBUG=False` because WhiteNoise doesn’t do bundle imports.  
- Planning is never perfect; multiple reworks are normal. This is why good programming practices are very important.    
- Git: switching branches, resolving conflicts, and understanding that `git pull` vs `git pull origin main` behave differently is crucial.
- Git: forgot to change my branch so many times, I am now a pro at git stashing :)
- PR workflow: merging too early can leave unfinished tasks; always double-check before closing a branch. Resolved multiple conflicts and survived! 
- JS is essential for dynamic UX (e.g., pop-ups) to avoid losing user input during CRUD operations on related entities like categories, units, or tags.
- novalidate

## My Struggles and What I’ve Learned:

- 404 pages don’t render with `DEBUG=False`; WhiteNoise helps serve static files.
  > Turns out it doesn't matter in PROD, nginx is used.
  
- CSS `@import` works in development but breaks after `collectstatic` + `DEBUG=False` because WhiteNoise doesn’t do bundle imports.
  > Haven't gotten to testing this on PROD, but it's not really an issue, I just link the files in the HTML/templates.
  
- Planning seems to never be enough; multiple reworks are normal. This is why good programming practices are very important.
  > Now I understand why dev teams have a planning stage. I've reworked every single thing on the project multiple times. I wish I had planned it better from the start, but I learned so much, maybe because I came without a plan. 
  
- Git: switching branches, resolving conflicts, and understanding that `git pull` vs `git pull origin main` behave differently is crucial.
- Git: forgot to change my branch so many times, I am now a pro at git stashing :)
- PR workflow: merging too early can leave unfinished tasks; always double-check before closing a branch. Resolved multiple conflicts and survived!
  
- JS is essential for dynamic UX (e.g., pop-ups) to avoid losing user input during CRUD operations on related entities like categories, units, or tags.
  > some things, such as calendars, are very hard to set up without JS. 
  
- novalidate only removes browser built-in validation — it has zero effect on server-side or database validation. Great for custom messages.

- Deploying the app in the same region as its dependencies is very important.
  > I may or may not have initially spun up an AWS machine in the US and hooked it up to Supabase in the EU. It may or may not have been extremely slow.

- Half of the security settings in Django need to be removed in production, actually. They interfere with Cloudflare. I outsourced some of the security to the lava lamps.

- Not all custom error templates are equal, some need special handling to be recognized by Django.

- Sentry is great for big errors, console in dev tools is great for JS chaos, print("DEBUG") is my passion.

- There is a middleware for every issue you first try to solve manually (such as API throttling).

- AI is great, but the moment you think "it's just a .gitignore, I won't read it" - you end up with migrations stripped from your git, only to be discovered days later after hours of debugging.

- vim
  > :wq  i can exit vim i can exit vim i can exit vim

- django is difficult to customize for front end when it comes to ready html elements like forms and inputs


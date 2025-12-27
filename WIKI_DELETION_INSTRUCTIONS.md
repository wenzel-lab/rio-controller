# Instructions for Deleting GitHub Wiki

## How to Delete a GitHub Wiki (Web Interface)

GitHub wikis are separate Git repositories. To delete a wiki:

### Method 1: Delete All Wiki Pages (Recommended)

1. **Navigate to your repository on GitHub:**
   - Go to: `https://github.com/wenzel-lab/modular-microfluidics-workstation-controller` (or your repo URL)

2. **Access the Wiki:**
   - Click on the **"Wiki"** tab in the repository navigation bar
   - Or go directly to: `https://github.com/wenzel-lab/modular-microfluidics-workstation-controller/wiki`

3. **Delete Individual Pages:**
   - Click on each wiki page
   - Scroll to the bottom of the page
   - Click **"Delete Page"** button
   - Confirm deletion
   - Repeat for all pages

4. **Alternative - Delete via Wiki Settings:**
   - Go to the Wiki main page
   - Look for a settings/gear icon (if available)
   - Some repositories have a "Delete Wiki" option in settings

### Method 2: Disable Wiki Feature

1. **Go to Repository Settings:**
   - Navigate to: `https://github.com/wenzel-lab/modular-microfluidics-workstation-controller/settings`
   - Or: Repository → Settings (gear icon in top right)

2. **Find Features Section:**
   - Scroll down to the **"Features"** section
   - Find **"Wikis"** checkbox
   - **Uncheck** the Wikis checkbox
   - This disables the wiki feature (pages remain but are hidden)

3. **To Completely Remove:**
   - After disabling, you may need to delete pages individually (Method 1)
   - Or contact GitHub support if you need to completely remove the wiki repository

### Method 3: Delete Wiki Repository via Git (Advanced)

If you have access to the wiki repository:

```bash
# Clone the wiki repository
git clone https://github.com/wenzel-lab/modular-microfluidics-workstation-controller.wiki.git

# Delete all files
cd modular-microfluidics-workstation-controller.wiki
rm -rf *
git add -A
git commit -m "Delete all wiki pages"
git push origin master
```

**Note:** The wiki repository URL is: `https://github.com/[org]/[repo].wiki.git`

### Important Notes

- **Backup First:** Before deleting, make sure all important content has been migrated to README files or other documentation
- **Wiki Content:** The current README references the wiki for installation instructions - this content should be integrated into `software/README.md` or `pi-deployment/README.md` before deletion
- **Design Decisions:** If the wiki contains valuable design decision documentation, ensure it's preserved in the repository (e.g., in `design-criteria.md` files)

### Recommended Workflow

1. ✅ Review all wiki pages and identify important content
2. ✅ Integrate important content into appropriate README files
3. ✅ Update README.md to remove wiki references (already done - installation link removed)
4. ✅ Delete wiki pages one by one via web interface
5. ✅ Disable wiki feature in repository settings

### Current Wiki References in Codebase

The README.md previously referenced:
- `[Software installation](https://github.com/wenzel-lab/moldular-microfluidics-workstation-controller/wiki/Install-the-Software)`

This has been replaced with links to:
- `software/README.md` - Comprehensive software documentation
- `pi-deployment/README.md` - Deployment instructions

All wiki content should now be integrated into the repository documentation.

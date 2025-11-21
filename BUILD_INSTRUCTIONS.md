# Fuzzkonnect - Build Instructions

This guide explains how to build a standalone executable from the Fuzzkonnect application.

## Prerequisites

1. **Python 3.8 or higher** installed on your system
2. **Git** (if cloning the repository)
3. **All project dependencies** installed

## Quick Start

### 1. Install Dependencies

First, install all required Python packages:

```bash
pip install -r requirements.txt
```

This will install:
- Flask (web framework)
- Pandas (data processing)
- RapidFuzz (fuzzy string matching)
- SciPy (optimization algorithms)
- Sentence Transformers (optional AI matching)
- PyInstaller (executable builder)

### 2. Build the Executable

Run PyInstaller with the provided spec file:

```bash
pyinstaller fuzzkonnect.spec
```

This command will:
- Create a `dist` folder
- Bundle all Python code and dependencies
- Include templates and data files
- Generate a single executable file

### 3. Find Your Executable

After building, the executable will be located at:

- **Windows**: `dist/Fuzzkonnect.exe`
- **macOS**: `dist/Fuzzkonnect`
- **Linux**: `dist/Fuzzkonnect`

## Platform-Specific Instructions

### Windows

1. Open Command Prompt or PowerShell
2. Navigate to the project directory:
   ```cmd
   cd path\to\FuzzyMatcher
   ```
3. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```
4. Build the executable:
   ```cmd
   pyinstaller fuzzkonnect.spec
   ```
5. The executable will be at: `dist\Fuzzkonnect.exe`

**Note**: Windows Defender or antivirus software may flag the executable. This is common with PyInstaller executables and is a false positive.

### macOS

1. Open Terminal
2. Navigate to the project directory:
   ```bash
   cd /path/to/FuzzyMatcher
   ```
3. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```
4. Build the executable:
   ```bash
   pyinstaller fuzzkonnect.spec
   ```
5. The executable will be at: `dist/Fuzzkonnect`

**Note**: macOS may require you to grant permission to run the app:
- Right-click the executable
- Select "Open"
- Click "Open" in the security dialog

### Linux

1. Open Terminal
2. Navigate to the project directory:
   ```bash
   cd /path/to/FuzzyMatcher
   ```
3. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```
4. Build the executable:
   ```bash
   pyinstaller fuzzkonnect.spec
   ```
5. The executable will be at: `dist/Fuzzkonnect`
6. Make it executable:
   ```bash
   chmod +x dist/Fuzzkonnect
   ```

## Running the Executable

Simply double-click the executable file. It will:

1. Start a local web server (on port 5000)
2. Automatically open your default web browser
3. Display the Fuzzkonnect interface

To stop the application:
- **Windows/Linux**: Press `CTRL+C` in the console window
- **macOS**: Press `CMD+C` in the Terminal, or close the console window

## Testing Before Distribution

Before distributing the executable, test it on a clean machine:

1. Copy the executable to a different computer
2. Double-click to run it
3. Verify that the web interface opens correctly
4. Test the field matching functionality with sample CSV files

## Customization Options

### Hiding the Console Window (Windows)

To hide the console window on Windows, edit `fuzzkonnect.spec`:

```python
exe = EXE(
    ...
    console=False,  # Change from True to False
    ...
)
```

Then rebuild:
```bash
pyinstaller fuzzkonnect.spec
```

### Adding an Application Icon

1. Create or obtain an icon file:
   - **Windows**: `.ico` format (e.g., `icon.ico`)
   - **macOS**: `.icns` format (e.g., `icon.icns`)
   - **Linux**: `.png` format (e.g., `icon.png`)

2. Place the icon file in the project directory

3. Edit `fuzzkonnect.spec`:
   ```python
   exe = EXE(
       ...
       icon='icon.ico',  # Update with your icon filename
       ...
   )
   ```

4. Rebuild:
   ```bash
   pyinstaller fuzzkonnect.spec
   ```

### Reducing Executable Size

The default build includes all dependencies. To reduce size:

1. **Disable AI matching** if not needed:
   - Remove `sentence-transformers` from `requirements.txt`
   - Remove from `hiddenimports` in `fuzzkonnect.spec`

2. **Use UPX compression** (already enabled in spec file):
   - Install UPX: https://upx.github.io/
   - PyInstaller will automatically use it

3. **Exclude unused packages**:
   - Add to `excludes` list in `fuzzkonnect.spec`

## Troubleshooting

### Build Fails with "Module not found"

**Solution**: Add the missing module to `hiddenimports` in `fuzzkonnect.spec`:

```python
hiddenimports = [
    'flask',
    'your_missing_module',  # Add here
    ...
]
```

### Executable is Very Large (>200MB)

**Cause**: Sentence Transformers and PyTorch add significant size.

**Solution**: Build without AI matching:
1. Remove sentence-transformers from requirements
2. Rebuild

### Antivirus Flags the Executable

**Cause**: PyInstaller executables are sometimes flagged as suspicious.

**Solution**:
- This is a false positive
- Submit the executable to your antivirus vendor for analysis
- Code sign the executable (advanced)

### Web Browser Doesn't Open Automatically

**Cause**: Browser permissions or firewall issues.

**Solution**:
- Manually open your browser
- Navigate to: http://127.0.0.1:5000

### Port 5000 Already in Use

**Solution**: Edit `launcher.py` and change:
```python
PORT = 5000  # Change to different port (e.g., 5001)
```

Then rebuild the executable.

## Distribution

The executable is self-contained and can be distributed by:

1. **Direct sharing**: Send the executable file via email or file sharing
2. **Installer**: Package with an installer (e.g., Inno Setup for Windows)
3. **Zip archive**: Compress and upload to a download server

**Important Notes**:
- Build on the same OS as your target users (Windows exe for Windows users, etc.)
- Include a README with usage instructions
- Test on a clean machine before distribution
- The executable is 50-200MB depending on included dependencies

## Development vs Distribution

### For Development (Normal Use):
```bash
python app.py
```

### For Distribution (Executable):
```bash
pyinstaller fuzzkonnect.spec
```

## Getting Help

If you encounter issues:
1. Check the console output for error messages
2. Review the PyInstaller documentation: https://pyinstaller.org/
3. Ensure all dependencies are correctly installed
4. Try rebuilding with `--clean` flag:
   ```bash
   pyinstaller --clean fuzzkonnect.spec
   ```

## Advanced: Cross-Platform Builds

**Note**: PyInstaller cannot cross-compile. To build for multiple platforms:

1. **Windows executable**: Build on Windows machine
2. **macOS executable**: Build on macOS machine
3. **Linux executable**: Build on Linux machine

Consider using CI/CD services (GitHub Actions, etc.) to automate multi-platform builds.

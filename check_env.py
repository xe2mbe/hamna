import sys
import pkg_resources

print("Python executable:", sys.executable)
print("\nPython path:")
for path in sys.path:
    print(f" - {path}")

print("\nInstalled packages:")
for pkg in sorted(pkg_resources.working_set, key=lambda x: x.key):
    print(f"{pkg.key}=={pkg.version}")

# Try to import gTTS
try:
    from gtts import gTTS
    print("\ngTTS is successfully imported!")
except ImportError as e:
    print(f"\nError importing gTTS: {e}")

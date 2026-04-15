import os
import time


def main() -> None:
  mode = os.getenv("CIEM_MODE", "local")
  print(f"ciem-factory worker started (mode={mode})")
  while True:
    # Placeholder loop for future async jobs (parse/graph/synthesis/validation).
    print("worker heartbeat")
    time.sleep(30)


if __name__ == "__main__":
  main()

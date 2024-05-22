"""Console script for tennis_preprocessing."""
import tennis_preprocessing

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command()
def main():
    """Console script for tennis_preprocessing."""
    console.print("Replace this message by putting your code into "
               "tennis_preprocessing.cli.main")
    console.print("See Typer documentation at https://typer.tiangolo.com/")
    


if __name__ == "__main__":
    app()

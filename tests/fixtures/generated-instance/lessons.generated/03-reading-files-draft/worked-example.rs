// A worked example for a different tool: reading a file and reporting the failure
// instead of panicking. The shape transfers; the program does not.

use std::process::exit;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let path = match args.get(1) {
        Some(value) => value,
        None => {
            eprintln!("usage: echofile <file>");
            exit(2);
        }
    };

    match std::fs::read_to_string(path) {
        Ok(text) => print!("{text}"),
        Err(error) => {
            eprintln!("echofile: {path}: {error}");
            exit(1);
        }
    }
}

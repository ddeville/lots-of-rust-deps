import os
import shutil
import subprocess

MAIN_CRATE_NAME = "so_many_deps"
DEP_NAME_PREFIX = "some_long_and_annoying_name_"
FUNCTION_PREFIX = "some_function_"

def generate_workspace(out: str, deps_count: int):
    for idx in range(deps_count):
        name = DEP_NAME_PREFIX + str(idx)
        src = os.path.join(out, name, "src")
        os.makedirs(src)

        with open(os.path.join(src, "lib.rs"), "w") as f:
            f.write(f"pub fn {FUNCTION_PREFIX + str(idx)}() {{\n")
            f.write("    println!(\"hello\");\n")
            f.write("}")

    src = os.path.join(out, MAIN_CRATE_NAME, "src")
    os.makedirs(src)

    with open(os.path.join(src, "lib.rs"), "w") as f:
        f.write("\n".join(["use " + DEP_NAME_PREFIX + str(i) + "::" + FUNCTION_PREFIX + str(i) + ";" for i in range(deps_count)]))
        f.write("\n\n")
        f.write("pub fn main() {\n")
        f.write("\n".join(["    " + FUNCTION_PREFIX + str(i) + "();" for i in range(deps_count)]))
        f.write("\n}\n")

def build_workspace(out: str, deps_count: int, target: str):
    build_dir = os.path.join(out, "build")
    os.makedirs(build_dir)

    base_args = [
        "--edition=2018",
        "--error-format=human",
        "--codegen=opt-level=0",
        "--codegen=debuginfo=0",
        "--codegen=codegen-units=16",
        "--codegen=debug-assertions=on",
        "--codegen=embed-bitcode=no",
        "--emit=dep-info,link",
        "--color=always",
    ]

    deps = []
    for idx in range(deps_count):
        name = DEP_NAME_PREFIX + str(idx)
        os.makedirs(os.path.join(build_dir, name))
        args = [
            os.path.join(out, name, "src", "lib.rs"),
            "--crate-name=" + name,
            "--crate-type=rlib",
            "--target=" + target,
            "--out-dir=" + os.path.join(build_dir, name),
            *base_args,
        ]
        deps.append(name)
        print("Building", name)
        subprocess.check_call(["rustc"] + args)

    name = MAIN_CRATE_NAME
    os.makedirs(os.path.join(build_dir, name))
    args = [
        os.path.join(out, name, "src", "lib.rs"),
        "--crate-name=" + name,
        "--crate-type=cdylib",
        "--target=" + target,
        "--out-dir=" + os.path.join(build_dir, name),
        *base_args,
        *["--extern=" + name + "=" + os.path.join(build_dir, name, "lib" + name + ".rlib") for name in deps],
        *["-Ldependency=" + os.path.join(build_dir, name) for name in deps],
    ]

    print("Building", name)

    param_file_path = os.path.join(build_dir, name + ".params")
    with open(param_file_path, "w") as f:
        content = "\n".join(args)
        f.write(content)
        print("Param file length:", len(content))

    subprocess.check_call(["rustc", "@" + param_file_path])


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "out")
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)

    deps_count = 10
    target = "x86_64-apple-darwin"

    generate_workspace(out_dir, deps_count)
    build_workspace(out_dir, deps_count, target)

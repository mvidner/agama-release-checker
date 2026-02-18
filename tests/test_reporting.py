from agama_release_checker.reporting import print_markdown_table


def test_print_markdown_table(capsys):
    headers = ["Country", "Home computer"]
    rows = [
        ["UK", "ZX Spectrum"],
        ["CS", "Didaktik Gama"],
    ]

    print_markdown_table(headers, rows)

    captured = capsys.readouterr()
    expected_output = (
        "| Country | Home computer |\n"
        "|---------|---------------|\n"
        "| UK      | ZX Spectrum   |\n"
        "| CS      | Didaktik Gama |\n"
    )
    assert captured.out == expected_output

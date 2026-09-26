import unittest

from scriptLattes.producoesUnitarias.atuacaoProfissional import AtuacaoProfissional


def make_atp(html_snippet):
    # O parser espera o item completo; podemos passar diretamente
    return AtuacaoProfissional(idMembro='test', partesDoItem=['', html_snippet])


class TestAtuacaoProfissional(unittest.TestCase):
    def test_institution_extracted_from_div(self):
        html = "<div class=\"inst_back\"><b>Universidade XYZ</b></div> Vínculo: Colaborador"
        atp = make_atp(html)
        self.assertEqual(atp.instituicao, "Universidade XYZ")
        self.assertEqual(atp.vinculo, "Colaborador")

    def test_institution_extracted_before_vinculo_when_no_div(self):
        html = "Universidade ABC Vínculo: Professor"
        atp = make_atp(html)
        self.assertEqual(atp.instituicao, "Universidade ABC")
        self.assertEqual(atp.vinculo, "Professor")

    def test_institution_extracted_before_vinculo_malformed_encoding(self):
        html = "Instituto DEF VÃ­nculo: Pesquisador"
        atp = make_atp(html)
        self.assertEqual(atp.instituicao, "Instituto DEF")
        self.assertEqual(atp.vinculo, "Pesquisador")

    def test_missing_institution_results_empty(self):
        html = "Vínculo: Colaborador"
        atp = make_atp(html)
        self.assertIn(atp.instituicao, ("", None))
        self.assertEqual(atp.vinculo, "Colaborador")


if __name__ == '__main__':
    unittest.main()

from django.db import models


class Lead(models.Model):
    STATUS_CHOICES = [
        ("novo", "Novo"),
        ("contatado", "Contatado"),
        ("respondeu", "Respondeu"),
        ("negociando", "Em negociação"),
        ("convertido", "Convertido"),
        ("perdido", "Perdido"),
    ]

    empresa = models.CharField(max_length=150)
    nome_contato = models.CharField(max_length=150, blank=True)
    nicho = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    telefone = models.CharField(max_length=30, blank=True)
    site_atual = models.URLField(blank=True)
    oportunidade = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="novo",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.empresa
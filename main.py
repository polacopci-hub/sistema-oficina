import flet as ft
from supabase import create_client, Client
from fpdf import FPDF
import datetime
import os
import re
import urllib.parse 

# --- SUAS CHAVES ---
SUPABASE_URL = "https://mwqwceayaouowgehuukf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im13cXdjZWF5YW91b3dnZWh1dWtmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzA2NjYzMDEsImV4cCI6MjA4NjI0MjMwMX0.5ItH8uAEEcHxDkew18e_kaGFkgIkfp5LaMM60RjT0U0"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Conectado ao Banco de Dados!")
except Exception as e:
    print(f"Erro no Banco: {e}")

def main(page: ft.Page):
    print("Iniciando App V25...")
    page.title = "Oficina V25 (Relatório Completo)"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = "adaptive"
    page.window_width = 390
    page.window_height = 844

    # Variáveis de Estado
    usuario_atual = {"id": None, "nome": None, "setor": None}
    dados_atuais = []
    
    # Controle de Edição (Se estiver preenchido, estamos editando)
    id_em_edicao = {"id": None} 

    # --- FUNÇÕES AUXILIARES ---
    def limpar_nome_arquivo(texto):
        s = texto.replace(" ", "_")
        return re.sub(r'[^a-zA-Z0-9_\-]', '', s)

    # --- GERADOR DE PDF (ATUALIZADO COM CLIENTE) ---
    def gerar_pdf_nuvem(lista_dados, periodo, nome_usuario):
        try:
            pdf = FPDF()
            pdf.add_page()
            
            # Títulos
            pdf.set_font("helvetica", "B", 16)
            pdf.cell(0, 10, "RELATORIO DE SERVICOS", align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", "", 10)
            pdf.cell(0, 10, f"Periodo: {periodo}", align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 10, f"Tecnico: {nome_usuario}", align="C", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)

            # Cabeçalho da Tabela
            pdf.set_fill_color(220, 220, 220)
            pdf.set_font("helvetica", "B", 8) # Fonte um pouco menor para caber tudo
            
            # Larguras: Data(20), Placa(20), Modelo(30), Cliente(35), Obs(Resto)
            pdf.cell(20, 8, "DATA", border=1, fill=True, align="C")
            pdf.cell(20, 8, "PLACA", border=1, fill=True, align="C")
            pdf.cell(30, 8, "MODELO", border=1, fill=True, align="C")
            pdf.cell(35, 8, "CLIENTE", border=1, fill=True, align="C") # NOVA COLUNA
            pdf.cell(0, 8, "OBSERVACOES", border=1, fill=True, align="C", new_x="LMARGIN", new_y="NEXT")

            # Linhas da Tabela
            pdf.set_font("helvetica", "", 7) # Fonte 7 para caber textos longos
            for item in lista_dados:
                data_fmt = f"{item['data_hora'][8:10]}/{item['data_hora'][5:7]}"
                
                # Corta textos para não quebrar layout
                modelo = item['modelo'][:15]
                cliente = item['cliente'][:20] # Corta nome muito longo
                obs_texto = (item['observacoes'][:55] + '..') if len(item['observacoes']) > 55 else item['observacoes']

                pdf.cell(20, 8, data_fmt, border=1, align="C")
                pdf.cell(20, 8, item['placa'], border=1, align="C")
                pdf.cell(30, 8, modelo, border=1, align="C")
                pdf.cell(35, 8, cliente, border=1, align="C") # NOVA COLUNA
                pdf.cell(0, 8, obs_texto, border=1, new_x="LMARGIN", new_y="NEXT")

            data_hoje = datetime.datetime.now().strftime("%Y-%m-%d")
            nome_user_limpo = limpar_nome_arquivo(nome_usuario)
            nome_arq = f"Relatorio_{nome_user_limpo}_{data_hoje}.pdf"
            
            pdf.output(nome_arq)

            with open(nome_arq, "rb") as f:
                supabase.storage.from_("relatorios").upload(
                    path=nome_arq, 
                    file=f, 
                    file_options={"content-type": "application/pdf", "x-upsert": "true"}
                )
            
            url = supabase.storage.from_("relatorios").get_public_url(nome_arq)
            os.remove(nome_arq) 
            return url
        except Exception as ex:
            print(f"Erro PDF: {ex}")
            return None

    # --- TELA DE CADASTRO ---
    def tela_cadastro():
        page.clean()
        
        txt_novo_nome = ft.TextField(label="Seu Nome Completo (Login)")
        txt_novo_setor = ft.TextField(label="Seu Setor (Ex: Pintura)")
        txt_novo_pin = ft.TextField(label="Crie uma Senha PIN (Números)", keyboard_type="number", password=True)
        txt_msg_erro = ft.Text("", color="red") 
        
        btn_salvar_cad = ft.FilledButton("SALVAR CADASTRO", width=300, height=50)

        def salvar_usuario(e):
            txt_msg_erro.value = "Processando..."
            txt_msg_erro.color = "blue"
            page.update()

            if not txt_novo_nome.value or not txt_novo_pin.value or not txt_novo_setor.value:
                txt_msg_erro.value = "Erro: Preencha todos os campos!"
                txt_msg_erro.color = "red"
                page.update()
                return

            try:
                res_check = supabase.table("usuarios").select("id").ilike("nome", txt_novo_nome.value).execute()
                if res_check.data:
                    txt_msg_erro.value = "Erro: Este nome já existe!"
                    txt_msg_erro.color = "red"
                    page.update()
                    return

                dados = {
                    "nome": txt_novo_nome.value,
                    "pin": txt_novo_pin.value,
                    "setor": txt_novo_setor.value, 
                    "ativo": True 
                }
                supabase.table("usuarios").insert(dados).execute()
                tela_login()

            except Exception as ex:
                txt_msg_erro.value = f"Erro técnico: {ex}"
                txt_msg_erro.color = "red"
                page.update()

        btn_salvar_cad.on_click = salvar_usuario

        page.add(
            ft.Column([
                ft.Text("CRIAR CONTA", size=25, weight="bold", color="blue"),
                ft.Text("Preencha seus dados", size=14, color="grey"),
                ft.Divider(color="transparent"),
                txt_novo_nome,
                txt_novo_setor,
                txt_novo_pin,
                txt_msg_erro, 
                ft.Divider(color="transparent"),
                btn_salvar_cad,
                ft.TextButton("Voltar para Login", on_click=lambda e: tela_login())
            ], alignment="center", horizontal_alignment="center")
        )

    # --- TELA DE LOGIN ---
    def tela_login():
        page.clean()
        page.appbar = None
        
        txt_login_nome = ft.TextField(label="Digite seu Nome de Usuário", width=300)
        txt_login_pin = ft.TextField(label="Senha PIN", password=True, width=150, text_align="center", keyboard_type="number")
        txt_aviso_login = ft.Text("", color="red", size=16, weight="bold")
        
        btn_entrar = ft.FilledButton("ENTRAR", width=200, height=50)

        def logar(e):
            txt_aviso_login.value = "Verificando..."
            txt_aviso_login.color = "blue"
            btn_entrar.disabled = True
            page.update()

            if not txt_login_nome.value or not txt_login_pin.value:
                txt_aviso_login.value = "Erro: Digite Nome e Senha!"
                txt_aviso_login.color = "red"
                btn_entrar.disabled = False
                page.update()
                return
            
            try:
                res_user = supabase.table("usuarios").select("*").ilike("nome", txt_login_nome.value).execute()
                
                if not res_user.data:
                    txt_aviso_login.value = "Usuário não encontrado!\nCrie uma conta nova."
                    txt_aviso_login.color = "red"
                else:
                    user = res_user.data[0]
                    if user['pin'] == txt_login_pin.value:
                        if user['ativo']:
                            usuario_atual.update(user)
                            sistema_principal()
                            return 
                        else:
                             txt_aviso_login.value = "Usuário bloqueado/inativo."
                             txt_aviso_login.color = "orange"
                    else:
                        txt_aviso_login.value = "Senha Incorreta!"
                        txt_aviso_login.color = "red"
                
                btn_entrar.disabled = False
                page.update()

            except Exception as ex:
                txt_aviso_login.value = f"Erro de conexão: {ex}"
                btn_entrar.disabled = False
                page.update()

        btn_entrar.on_click = logar

        page.add(
            ft.Column([
                ft.Text("OFICINA APP", size=30, weight="bold", color="blue"),
                ft.Text("Login Seguro", size=12, color="grey"),
                ft.Divider(height=20, color="transparent"),
                
                txt_login_nome,
                txt_login_pin, 
                txt_aviso_login, 
                btn_entrar,
                
                ft.Divider(),
                ft.Text("Não tem acesso?"),
                ft.OutlinedButton("CRIAR CONTA NOVA", on_click=lambda e: tela_cadastro(), width=200)
                
            ], alignment="center", horizontal_alignment="center")
        )

    # --- SISTEMA PRINCIPAL ---
    def sistema_principal():
        page.clean()
        
        # ABA 1: NOVA OS / EDIÇÃO
        lbl_titulo_os = ft.Text("NOVA ORDEM DE SERVICO", size=18, weight="bold")
        txt_placa = ft.TextField(label="Placa")
        txt_modelo = ft.TextField(label="Modelo")
        txt_cliente = ft.TextField(label="Cliente")
        txt_obs = ft.TextField(
            label="O que foi feito? (Observações)", 
            multiline=True, 
            min_lines=3,
            max_lines=5,
            hint_text="Use o microfone do teclado..."
        )
        
        btn_salvar_os = ft.FilledButton("SALVAR REGISTRO", width=300, height=50)
        btn_cancelar_edicao = ft.TextButton("Cancelar Edição", visible=False) 

        def resetar_formulario():
            id_em_edicao['id'] = None
            lbl_titulo_os.value = "NOVA ORDEM DE SERVICO"
            lbl_titulo_os.color = "black"
            btn_salvar_os.text = "SALVAR REGISTRO"
            btn_cancelar_edicao.visible = False
            txt_placa.value = ""
            txt_modelo.value = ""
            txt_cliente.value = ""
            txt_obs.value = ""
            page.update()

        btn_cancelar_edicao.on_click = lambda e: resetar_formulario()

        def salvar_os(e):
            btn_salvar_os.text = "Salvando..."
            btn_salvar_os.disabled = True
            page.update()

            if not txt_obs.value and not txt_placa.value: 
                page.snack_bar = ft.SnackBar(ft.Text("Preencha Placa e Observação!"))
                page.snack_bar.open = True
                btn_salvar_os.text = "SALVAR"
                btn_salvar_os.disabled = False
                page.update()
                return
                
            try:
                dados = {
                    "usuario_id": usuario_atual['id'], 
                    "placa": txt_placa.value, 
                    "modelo": txt_modelo.value, 
                    "cliente": txt_cliente.value, 
                    "lista_servicos": "-", 
                    "observacoes": txt_obs.value, 
                    "status": "Finalizado"
                }

                if id_em_edicao['id']:
                    # UPDATE
                    supabase.table("servicos").update(dados).eq("id", id_em_edicao['id']).execute()
                    page.snack_bar = ft.SnackBar(ft.Text("Atualizado com sucesso!"), bgcolor="blue")
                else:
                    # INSERT
                    supabase.table("servicos").insert(dados).execute()
                    page.snack_bar = ft.SnackBar(ft.Text("Salvo com sucesso!"), bgcolor="green")
                
                page.snack_bar.open = True
                resetar_formulario()
                btn_salvar_os.disabled = False
                page.update()

            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Erro: {ex}"), bgcolor="red")
                page.snack_bar.open = True
                btn_salvar_os.disabled = False
                page.update()

        btn_salvar_os.on_click = salvar_os

        conteudo_nova_os = ft.Column([
            lbl_titulo_os,
            txt_placa, txt_modelo, txt_cliente,
            ft.Divider(), 
            txt_obs,
            btn_salvar_os,
            btn_cancelar_edicao
        ])

        # ABA 2: HISTORICO
        txt_dt_ini = ft.TextField(label="Início", value="2026-02-01", width=140)
        txt_dt_fim = ft.TextField(label="Fim", value="2026-02-28", width=140)
        lista_cards = ft.Column()
        
        btn_gerar = ft.ElevatedButton("GERAR LINK PDF", icon=None)
        btn_buscar = ft.FilledButton("FILTRAR / BUSCAR", width=300, height=45)

        def acao_gerar(e):
            if not dados_atuais: return
            btn_gerar.text = "PROCESSANDO..."
            btn_gerar.disabled = True
            page.update()
            periodo = f"{txt_dt_ini.value} a {txt_dt_fim.value}"
            url_pdf = gerar_pdf_nuvem(dados_atuais, periodo, usuario_atual['nome'])
            if url_pdf:
                msg = f"Olá, segue o relatório ({periodo}): {url_pdf}"
                msg_encoded = urllib.parse.quote(msg)
                link_zap = f"https://wa.me/?text={msg_encoded}"
                btn_gerar.text = "ABRIR WHATSAPP AGORA"
                btn_gerar.style = ft.ButtonStyle(bgcolor="green", color="white")
                btn_gerar.url = link_zap 
                btn_gerar.disabled = False
                btn_gerar.on_click = None 
                page.update()
            else:
                btn_gerar.text = "ERRO - TENTE DE NOVO"
                btn_gerar.disabled = False
                page.update()

        btn_gerar.on_click = acao_gerar
        btn_gerar.visible = False

        # --- FUNÇÕES ESPECIAIS (SEM POP-UP) ---
        def deletar_item(item_id):
            try:
                supabase.table("servicos").delete().eq("id", item_id).execute()
                buscar(None) 
            except: pass

        def preparar_edicao(item):
            id_em_edicao['id'] = item['id']
            txt_placa.value = item['placa']
            txt_modelo.value = item['modelo']
            txt_cliente.value = item['cliente']
            txt_obs.value = item['observacoes']
            
            lbl_titulo_os.value = f"EDITANDO REGISTRO #{item['id']}"
            lbl_titulo_os.color = "orange"
            btn_salvar_os.text = "SALVAR ALTERAÇÕES"
            btn_cancelar_edicao.visible = True
            
            trocar_tela("NOVA OS")

        def buscar(e):
            lista_cards.controls.clear()
            lista_cards.controls.append(ft.ProgressBar())
            dados_atuais.clear()
            btn_gerar.visible = False
            if e: btn_buscar.text = "Buscando..."
            page.update()
            
            try:
                ini = f"{txt_dt_ini.value}T00:00:00"
                fim = f"{txt_dt_fim.value}T23:59:59"
                q = supabase.table("servicos").select("*").gte("data_hora", ini).lte("data_hora", fim).order("id", desc=True)
                if usuario_atual['setor'].lower() != 'admin': q = q.eq("usuario_id", usuario_atual['id'])
                
                dados = q.execute().data
                lista_cards.controls.clear()
                
                if not dados: 
                    lista_cards.controls.append(ft.Text("Nenhum registro encontrado."))
                else:
                    dados_atuais.extend(dados)
                    btn_gerar.text = "GERAR LINK PDF"
                    btn_gerar.style = None
                    btn_gerar.url = None 
                    btn_gerar.on_click = acao_gerar
                    btn_gerar.disabled = False
                    btn_gerar.visible = True 
                    
                    for item in dados:
                        obs_curta = (item['observacoes'][:50] + '...') if len(item['observacoes']) > 50 else item['observacoes']
                        
                        btn_editar = ft.TextButton("[EDITAR]", on_click=lambda e, i=item: preparar_edicao(i))
                        btn_excluir = ft.TextButton("[EXCLUIR]", style=ft.ButtonStyle(color="red"), on_click=lambda e, id=item['id']: deletar_item(id))

                        card = ft.Container(
                            padding=10, border=ft.Border.all(1, "grey"), border_radius=8,
                            content=ft.Column([
                                ft.Row([
                                    ft.Text(f"PLACA: {item['placa']}", weight="bold"),
                                    ft.Text(f"{item['data_hora'][8:10]}/{item['data_hora'][5:7]}", color="grey")
                                ], alignment="spaceBetween"),
                                ft.Text(f"Veículo: {item['modelo']}"),
                                ft.Text(f"Cliente: {item['cliente']}", size=12),
                                ft.Text(f"Feito: {obs_curta}", color="blue"),
                                ft.Divider(),
                                ft.Row([ft.Text("Ações:", color="grey"), btn_editar, btn_excluir], alignment="end")
                            ])
                        )
                        lista_cards.controls.append(card)
            except Exception as ex:
                lista_cards.controls.clear()
                lista_cards.controls.append(ft.Text(f"Erro: {ex}"))
            
            btn_buscar.text = "FILTRAR / BUSCAR"
            btn_buscar.disabled = False
            page.update()

        btn_buscar.on_click = buscar

        conteudo_historico = ft.Column([
            ft.Text("HISTÓRICO", size=18, weight="bold"),
            ft.Row([txt_dt_ini, txt_dt_fim]),
            btn_buscar,
            ft.Divider(),
            btn_gerar,
            ft.Divider(),
            lista_cards
        ])

        area_conteudo = ft.Container(content=conteudo_nova_os)

        def trocar_tela(nome_tela):
            if nome_tela == "NOVA OS": area_conteudo.content = conteudo_nova_os
            elif nome_tela == "HISTORICO": area_conteudo.content = conteudo_historico
            page.update()

        topo = ft.Container(
            bgcolor="blue", padding=10,
            content=ft.Row([
                ft.Text(f"Olá, {usuario_atual['nome']}", color="white", weight="bold"),
                ft.FilledButton("SAIR", on_click=lambda e: tela_login(), style=ft.ButtonStyle(bgcolor="red"))
            ], alignment="spaceBetween")
        )

        menu = ft.Row([
            ft.FilledButton("NOVA OS", on_click=lambda e: trocar_tela("NOVA OS"), expand=True),
            ft.FilledButton("HISTORICO", on_click=lambda e: trocar_tela("HISTORICO"), expand=True)
        ])

        page.add(topo)
        page.add(menu)
        page.add(ft.Divider())
        page.add(area_conteudo)

    tela_login()

ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8550, host="0.0.0.0")
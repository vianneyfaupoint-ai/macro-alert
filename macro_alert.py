EVENT_EXPLAINERS = {
    "non-farm": "📈 Le chiffre le plus important du mois — au dessus du consensus = dollar fort = US30 up",
    "nfp": "📈 Le chiffre le plus important du mois — au dessus du consensus = dollar fort = US30 up",
    "payroll": "📈 Emploi US — bon chiffre = économie solide = haussier",
    "cpi": "🔥 Inflation — chiffre élevé = Fed garde les taux hauts = baissier pour les actions",
    "consumer price": "🔥 Inflation — chiffre élevé = Fed garde les taux hauts = baissier",
    "pce": "🔥 Inflation préférée de la Fed — très surveillée",
    "fomc": "🏦 Décision taux Fed — le plus gros catalyseur possible",
    "interest rate": "🏦 Décision taux Fed — le plus gros catalyseur possible",
    "fed": "🏦 Discours Fed — chaque mot peut bouger le marché",
    "powell": "🏦 Discours Powell — attention à la volatilité",
    "warsh": "🏦 Nouveau président Fed — ses premiers mots sont clés",
    "ism": "🏭 Activité économique — au dessus de 50 = expansion = haussier",
    "pmi": "🏭 Activité économique — au dessus de 50 = expansion = haussier",
    "gdp": "💰 Croissance US — bon chiffre = haussier",
    "retail sales": "🛒 Consommation — moteur de l'économie US",
    "consumer confidence": "😊 Moral des ménages — indicateur avancé de consommation",
    "michigan": "😊 Moral des ménages — indicateur avancé de consommation",
    "unemployment": "👷 Chômage — hausse = mauvais signe pour l'économie",
    "jobless claims": "👷 Inscriptions chômage hebdo — surveiller la tendance",
    "adp": "👷 Emploi privé — avant-goût du NFP du vendredi",
    "jolts": "👷 Offres d'emploi — mesure la tension du marché du travail",
    "ppi": "🏭 Inflation producteurs — précurseur du CPI",
    "producer price": "🏭 Inflation producteurs — précurseur du CPI",
    "durable goods": "🔧 Commandes industrie — indicateur d'investissement",
    "beige book": "📖 Rapport Fed sur l'économie réelle — ton du prochain FOMC",
    "fomc member": "🏦 Discours membre Fed — peut signaler un changement de politique",
    "trade balance": "🌍 Balance commerciale — déficit = dollar sous pression",
    "new home sales": "🏠 Immobilier — sensible aux taux d'intérêt",
    "building permits": "🏠 Construction — indicateur avancé de l'immobilier",
}


def get_explainer(event_name):
    name_lower = event_name.lower()
    for keyword, explanation in EVENT_EXPLAINERS.items():
        if keyword in name_lower:
            return explanation
    return None


def build_message(events):
    now = datetime.now(PARIS_TZ)
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    mois = ["jan", "fév", "mars", "avr", "mai", "juin",
            "juil", "août", "sep", "oct", "nov", "déc"]
    date_str = f"{jours[now.weekday()]} {now.day} {mois[now.month-1]} {now.year}"

    high = [e for e in events if e["high_impact"]]
    medium = [e for e in events if not e["high_impact"]]

    lines = [f"📊 *Macro US — {date_str}*", "_Briefing US30 · Heure Paris_", ""]

    if not events:
        lines += [
            "✅ *Aucun event macro majeur*",
            "_Séance pilotée par la géopolitique_",
            "_→ Surveiller Iran · Détroit · Pétrole · Trump_",
        ]
    else:
        if high:
            lines.append("🔴 *Fort impact*")
            for e in high:
                paris = convert_ny_to_paris(e["time_ny"])
                lines.append(f"  `{paris}` — *{e['name']}*")
                details = []
                if e["forecast"]:
                    details.append(f"Cns: `{e['forecast']}`")
                if e["previous"]:
                    details.append(f"Préc: `{e['previous']}`")
                if e["actual"]:
                    details.append(f"✅ Réel: `{e['actual']}`")
                if details:
                    lines.append(f"    └ {' · '.join(details)}")
                explainer = get_explainer(e["name"])
                if explainer:
                    lines.append(f"    💡 _{explainer}_")
            lines.append("")

        if medium:
            lines.append("🟡 *Impact moyen*")
            for e in medium:
                paris = convert_ny_to_paris(e["time_ny"])
                cns = f" _(cns: {e['forecast']})_" if e["forecast"] else ""
                lines.append(f"  `{paris}` — {e['name']}{cns}")
                explainer = get_explainer(e["name"])
                if explainer:
                    lines.append(f"    💡 _{explainer}_")
            lines.append("")

    lines += [
        "─────────────────",
        "⏰ *Ouverture* : `14h30` Paris",
        "🎯 *Fenêtre* : `14h30 → 15h30`",
        "📌 *ATH US30* : `50 539 pts`",
        "",
        "🌍 *Watch* : Iran · Détroit · Pétrole · Trump",
        "",
        "_Bonne séance_ 📈",
    ]
    return "\n".join(lines)

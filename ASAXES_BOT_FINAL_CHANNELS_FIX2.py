import asyncio
from pathlib import Path
import discord
from discord.ext import commands
from discord.ui import View, Button
import getpass, re

TOKEN=getpass.getpass("Discord BOT token (niewidoczny): ").strip()
if not TOKEN: raise SystemExit("Brak tokena.")

intents=discord.Intents.default()
intents.guilds=True
intents.members=True
intents.message_content=True
bot=commands.Bot(command_prefix="!",intents=intents)

ROLES=[
("minecraft","🟢 Minecraft"),("fortnite","🔵 Fortnite"),("roblox","🟣 Roblox"),
("gta","🔴 GTA"),("cs2","🟡 CS2"),("valorant","🟠 Valorant"),
("fs25","🚜 Farming Simulator 25"),("ets2","🚛 Euro Truck Simulator 2"),
("rf4","🎣 Russian Fishing 4"),("muzyka","🎵 Muzyka"),("filmy","🎬 Filmy"),
("sport","⚽ Sport"),("tech","💻 Technologia"),("sztuka","🎨 Sztuka"),
("foto","📸 Fotografia"),("live","🔴 LIVE"),("filmyn","🎬 FILMY"),
("eventy","🎁 EVENTY"),("wazne","📢 WAŻNE"),("czerwony","🔴 Czerwony"),
("niebieski","🔵 Niebieski"),("fioletowy","🟣 Fioletowy"),("zielony","🟢 Zielony")
]

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Otwórz ticket",
        emoji="🎫",
        style=discord.ButtonStyle.primary,
        custom_id="asaxes_ticket"
    )
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        member = interaction.user

        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "", member.name.lower())[:20] or "user"
        channel_name = f"ticket-{safe_name}"

        existing = discord.utils.get(guild.text_channels, name=channel_name)
        if existing:
            await interaction.followup.send(f"🎫 Masz już ticket: {existing.mention}", ephemeral=True)
            return

        category = discord.utils.get(guild.categories, name="🎫 TICKETY")
        if category is None:
            category = await guild.create_category("🎫 TICKETY", reason="ASAXES tickets")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        # Staff can see tickets.
        for role_name in ["👑 ASAXES", "🧠 Zastępca", "⚙️ Administrator", "🛡️ Moderator", "🔨 Trial Moderator"]:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                )

        try:
            channel = await guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites,
                reason="ASAXES ticket"
            )
            await channel.send(
                f"🎫 **Ticket {member.mention}**\n\n"
                "Opisz tutaj, w czym potrzebujesz pomocy. 🛡️"
            )
            await interaction.followup.send(
                f"✅ Ticket utworzony: {channel.mention}", ephemeral=True
            )
            await send_log(
                guild,
                f"🎫 **Utworzono ticket**\n👤 {member.mention}\n📁 {channel.mention}"
            )
        except Exception as e:
            print(f"BŁĄD TICKETU: {e!r}", flush=True)
            await interaction.followup.send(
                "❌ Nie udało się utworzyć ticketu. Sprawdź uprawnienia bota.",
                ephemeral=True
            )

class VerifyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Akceptuję regulamin",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="asaxes_accept_rules"
    )
    async def accept(self, interaction: discord.Interaction, button: Button):
        try:
            await interaction.response.defer(ephemeral=True)
            role = discord.utils.get(interaction.guild.roles, name="👀 Widz")
            if role is None:
                role = await interaction.guild.create_role(
                    name="👀 Widz",
                    colour=discord.Colour(0x95A5A6),
                    reason="ASAXES verification"
                )
            if role >= interaction.guild.me.top_role:
                await interaction.edit_original_response(
                    content="❌ Rola 👀 Widz jest za wysoko. Przenieś rolę ASAXES Setup wyżej niż 👀 Widz."
                )
                return
            await interaction.user.add_roles(role, reason="Akceptacja regulaminu ASAXES")
            await interaction.edit_original_response(
                content="✅ **Regulamin zaakceptowany!** Nadano Ci rolę **👀 Widz**."
            )
            await send_log(
                interaction.guild,
                f"🔐 **Regulamin zaakceptowany**\n👤 {interaction.user.mention}\n🏷️ 👀 Widz"
            )
        except discord.Forbidden:
            try:
                await interaction.edit_original_response(
                    content="❌ Bot nie ma uprawnień do nadania roli 👀 Widz."
                )
            except Exception:
                pass
        except Exception as e:
            print(f"BŁĄD WERYFIKACJI: {e!r}", flush=True)


# =========================
# 🏆 XP + POZIOMY + 💰 PUNKTY
# =========================
import json
import random
import time

XP_FILE = "asaxes_xp.json"
XP_COOLDOWN = 30
xp_cooldowns = {}

def load_xp_data():
    try:
        with open(XP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_xp_data(data):
    tmp = XP_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    Path(tmp).replace(XP_FILE)

XP_DATA = load_xp_data()

LEVEL_REWARDS = {
    5:  ("🏆 Poziom 5",  "Nagroda za aktywność — poziom 5"),
    10: ("🥇 Poziom 10", "Nagroda za aktywność — poziom 10"),
    20: ("💎 Poziom 20", "Nagroda za aktywność — poziom 20"),
    30: ("👑 Poziom 30", "Nagroda za aktywność — poziom 30"),
}

def user_stats(user_id):
    key = str(user_id)
    if key not in XP_DATA:
        XP_DATA[key] = {"xp": 0, "level": 0, "points": 0, "messages": 0}
    return XP_DATA[key]

def xp_needed(level):
    return 100 + (level * 50)

def calculate_level(total_xp):
    level = 0
    while total_xp >= xp_needed(level):
        total_xp -= xp_needed(level)
        level += 1
    return level, total_xp

async def ensure_level_role(guild, level):
    if level not in LEVEL_REWARDS:
        return None
    name, _ = LEVEL_REWARDS[level]
    role = discord.utils.get(guild.roles, name=name)
    if role is None:
        try:
            role = await guild.create_role(
                name=name,
                colour=discord.Colour(0xF1C40F),
                reason="ASAXES nagroda za poziom"
            )
        except Exception as e:
            print(f"BŁĄD TWORZENIA NAGRODY {name}: {e!r}", flush=True)
            return None
    return role

async def award_level_role(member, level):
    role = await ensure_level_role(member.guild, level)
    if role is None:
        return
    if role < member.guild.me.top_role and role not in member.roles:
        try:
            await member.add_roles(role, reason=f"ASAXES poziom {level}")
        except Exception as e:
            print(f"BŁĄD NADANIA NAGRODY: {e!r}", flush=True)

def format_rank(member):
    s = user_stats(member.id)
    level, current_xp = calculate_level(int(s.get("xp", 0)))
    need = xp_needed(level)
    return (
        f"🏆 **{member.display_name}**\n"
        f"⭐ Poziom: **{level}**\n"
        f"✨ XP: **{current_xp}/{need}**\n"
        f"💰 Punkty: **{s.get('points', 0)}**\n"
        f"💬 Wiadomości: **{s.get('messages', 0)}**"
    )

@bot.event
async def on_message(message):
    if message.author.bot or message.guild is None:
        return

    # XP naliczamy tylko zweryfikowanym użytkownikom.
    widz = discord.utils.get(message.guild.roles, name="👀 Widz")
    if widz and widz in message.author.roles:
        # Nie naliczamy XP w kanałach technicznych.
        excluded = {
            "👋・witaj", "📜・regulamin", "✅・akceptacja",
            "📋・logi", "🎫・tickety", "🚨・zgłoszenia"
        }
        if message.channel.name not in excluded:
            now = time.monotonic()
            last = xp_cooldowns.get(message.author.id, 0)
            if now - last >= XP_COOLDOWN and len(message.content.strip()) >= 2:
                xp_cooldowns[message.author.id] = now
                s = user_stats(message.author.id)
                old_level, _ = calculate_level(int(s.get("xp", 0)))
                s["xp"] = int(s.get("xp", 0)) + random.randint(8, 15)
                s["points"] = int(s.get("points", 0)) + random.randint(1, 3)
                s["messages"] = int(s.get("messages", 0)) + 1

                new_level, _ = calculate_level(s["xp"])
                save_xp_data(XP_DATA)

                if new_level > old_level:
                    await award_level_role(message.author, new_level)
                    if new_level in LEVEL_REWARDS:
                        reward_name = LEVEL_REWARDS[new_level][0]
                        await message.channel.send(
                            f"🎉 {message.author.mention} awansował na **poziom {new_level}**!\n"
                            f"🎁 Otrzymujesz nagrodę **{reward_name}**!"
                        )
                    else:
                        await message.channel.send(
                            f"🎉 {message.author.mention} awansował na **poziom {new_level}**!"
                        )

    await bot.process_commands(message)


# =========================
# 🎁 SKLEP ZA PUNKTY
# =========================
SHOP_ITEMS = {
    "vip": {
        "name": "💎 VIP",
        "price": 1000,
        "role": "💎 VIP",
        "description": "Rola VIP na serwerze."
    },
    "wspierajacy": {
        "name": "💜 Wspierający",
        "price": 500,
        "role": "💜 Wspierający",
        "description": "Rola Wspierający."
    },
    "czerwony": {
        "name": "🔴 Czerwony",
        "price": 200,
        "role": "🔴 Czerwony",
        "description": "Kolorowa rola profilu."
    },
    "niebieski": {
        "name": "🔵 Niebieski",
        "price": 200,
        "role": "🔵 Niebieski",
        "description": "Kolorowa rola profilu."
    },
    "fioletowy": {
        "name": "🟣 Fioletowy",
        "price": 200,
        "role": "🟣 Fioletowy",
        "description": "Kolorowa rola profilu."
    },
    "zielony": {
        "name": "🟢 Zielony",
        "price": 200,
        "role": "🟢 Zielony",
        "description": "Kolorowa rola profilu."
    },
}

def only_channel(channel_name):
    async def predicate(ctx):
        if ctx.channel.name != channel_name:
            try:
                await ctx.message.delete()
            except Exception:
                pass
            msg = await ctx.send(
                f"📍 Tej komendy używaj na kanale **#{channel_name}**."
            )
            await asyncio.sleep(5)
            try:
                await msg.delete()
            except Exception:
                pass
            return False
        return True
    return commands.check(predicate)

@bot.command(name="sklep")
@only_channel("🛒・sklep")
async def shop_command(ctx):
    lines = []
    for key, item in SHOP_ITEMS.items():
        lines.append(
            f"**{item['name']}** — 💰 **{item['price']} pkt**\n"
            f"↳ `{key}` • {item['description']}"
        )
    embed = discord.Embed(
        title="🛒 SKLEP ASAXES",
        description=(
            "Wydawaj zdobyte punkty na specjalne role.\n\n"
            + "\n\n".join(lines)
            + "\n\n💡 Kupowanie: `!kup nazwa`"
        ),
        colour=discord.Colour(0xE67E22)
    )
    embed.set_footer(text="ASAXES • Punkty za aktywność")
    await ctx.send(embed=embed)

@bot.command(name="kup")
@only_channel("🛒・sklep")
async def buy_command(ctx, item_key: str = None):
    if not item_key:
        await ctx.send("❌ Podaj nazwę przedmiotu, np. `!kup vip`.")
        return

    key = item_key.lower().strip()
    item = SHOP_ITEMS.get(key)
    if item is None:
        await ctx.send("❌ Nie ma takiej pozycji. Użyj `!sklep`.")
        return

    member = ctx.author
    s = user_stats(member.id)
    points = int(s.get("points", 0))

    if points < item["price"]:
        await ctx.send(
            f"❌ {member.mention}, potrzebujesz **{item['price'] - points} pkt** więcej."
        )
        return

    role = discord.utils.get(ctx.guild.roles, name=item["role"])
    if role is None:
        try:
            role = await ctx.guild.create_role(
                name=item["role"],
                reason="ASAXES sklep za punkty"
            )
        except Exception:
            await ctx.send("❌ Nie mogę utworzyć tej roli. Sprawdź uprawnienia bota.")
            return

    if role in member.roles:
        await ctx.send(f"ℹ️ {member.mention}, masz już rolę **{item['name']}**.")
        return

    if ctx.guild.me and role >= ctx.guild.me.top_role:
        await ctx.send(
            f"❌ Rola **{item['name']}** jest wyżej od najwyższej roli bota. "
            "Przenieś rolę bota wyżej w ustawieniach serwera."
        )
        return

    try:
        await member.add_roles(role, reason="ASAXES zakup za punkty")
        s["points"] = points - item["price"]
        save_xp_data(XP_DATA)
        await ctx.send(
            f"🎉 {member.mention} kupił(a) **{item['name']}** za "
            f"💰 **{item['price']} pkt**!\n"
            f"💰 Pozostało: **{s['points']} pkt**."
        )
    except Exception:
        await ctx.send("❌ Nie udało się nadać roli. Sprawdź hierarchię ról bota.")



@bot.command(name="asaxes")
async def asaxes_command(ctx):
    embed = discord.Embed(
        title="⭐ ASAXES — SYSTEM SERWERA",
        description=(
            "👋 Powitanie • 📜 Regulamin • ✅ Weryfikacja\n"
            "🎭 Role • 📋 Logi • 🎫 Tickety\n"
            "🏆 XP • ⭐ Poziomy • 💰 Punkty\n"
            "🛒 Sklep • 🎁 Nagrody • 🏆 Ranking\n\n"
            "Użyj `!rank`, `!punkty`, `!top`, `!sklep` lub `!nagrody`."
        ),
        colour=discord.Colour(0x9B59B6)
    )
    await ctx.send(embed=embed)


@bot.command(name="rank", aliases=["xp", "poziom"])
@only_channel("🏆・ranking")
async def rank_command(ctx):
    await ctx.send(embed=discord.Embed(
        title="🏆 TWÓJ RANKING",
        description=format_rank(ctx.author),
        colour=discord.Colour(0x9B59B6)
    ))

@bot.command(name="punkty")
@only_channel("💰・punkty")
async def points_command(ctx):
    s = user_stats(ctx.author.id)
    await ctx.send(
        f"💰 {ctx.author.mention}, masz **{s.get('points', 0)} punktów**."
    )

@bot.command(name="top", aliases=["ranking"])
@only_channel("🏆・ranking")
async def top_command(ctx):
    rows = []
    for uid, s in XP_DATA.items():
        try:
            member = ctx.guild.get_member(int(uid))
            if member:
                level, _ = calculate_level(int(s.get("xp", 0)))
                rows.append((int(s.get("xp", 0)), level, member.display_name, int(s.get("points", 0))))
        except Exception:
            pass
    rows.sort(reverse=True)

    if not rows:
        await ctx.send("🏆 Brak danych — zacznij pisać na serwerze!")
        return

    lines = []
    for i, (xp, level, name, points) in enumerate(rows[:10], 1):
        lines.append(f"**{i}.** {name} — ⭐ Lv. {level} • ✨ {xp} XP • 💰 {points} pkt")

    embed = discord.Embed(
        title="🏆 TOP 10 ASAXES",
        description="\n".join(lines),
        colour=discord.Colour(0xF1C40F)
    )
    await ctx.send(embed=embed)

@bot.command(name="nagrody")
@only_channel("🎁・nagrody")
async def rewards_command(ctx):
    lines = [
        f"⭐ **Poziom {lvl}** → {name}"
        for lvl, (name, _) in sorted(LEVEL_REWARDS.items())
    ]
    embed = discord.Embed(
        title="🎁 NAGRODY ZA AKTYWNOŚĆ",
        description="\n".join(lines) + "\n\n💬 Pisz na serwerze, zdobywaj XP i awansuj!",
        colour=discord.Colour(0x2ECC71)
    )
    await ctx.send(embed=embed)


async def send_log(guild, text):
    channel = discord.utils.get(guild.text_channels, name="📋・logi")
    if channel:
        try:
            await channel.send(text)
        except Exception as e:
            print(f"BŁĄD LOGÓW: {e!r}", flush=True)

class RoleButton(Button):
    def __init__(self,key,label):
        super().__init__(label=label,style=discord.ButtonStyle.secondary,
                         custom_id=f"asaxes_role_{key}")
        self.role_name=label

    async def callback(self,interaction:discord.Interaction):
        print(f"KLIK: {self.role_name} / {interaction.user} / {interaction.guild}", flush=True)
        try:
            await interaction.response.send_message(
                f"⏳ Ustawiam rolę **{self.role_name}**...",
                ephemeral=True
            )
        except Exception as e:
            print(f"BŁĄD ODPOWIEDZI DISCORD: {e!r}", flush=True)
            return
        try:
            role=discord.utils.get(interaction.guild.roles,name=self.role_name)
            if role is None:
                role=await interaction.guild.create_role(
                    name=self.role_name,reason="ASAXES wybór ról")
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role,reason="ASAXES wybór ról")
                text=f"❌ Usunięto rolę **{self.role_name}**."
                await send_log(
                    interaction.guild,
                    f"🎭 **Rola usunięta**\n👤 {interaction.user.mention}\n🏷️ {self.role_name}"
                )
            else:
                await interaction.user.add_roles(role,reason="ASAXES wybór ról")
                text=f"✅ Nadano rolę **{self.role_name}**."
                await send_log(
                    interaction.guild,
                    f"🎭 **Rola nadana**\n👤 {interaction.user.mention}\n🏷️ {self.role_name}"
                )
            try:
                await interaction.edit_original_response(content=text)
            except Exception as e:
                print(f"BŁĄD AKTUALIZACJI ODPOWIEDZI: {e!r}", flush=True)
        except Exception as e:
            print(f"BŁĄD KLIKNIĘCIA: {e!r}")
            try:
                await interaction.edit_original_response(
                    content="❌ Nie udało się zmienić roli. Sprawdź uprawnienia bota.")
            except Exception:
                pass

class RoleView(View):
    def __init__(self):
        super().__init__(timeout=None)
        for key,label in ROLES:
            self.add_item(RoleButton(key,label))


async def configure_new_user_visibility(guild):
    """Nowi widzą tylko onboarding; zweryfikowani (👀 Widz) widzą resztę."""
    visible_names = {"👋・witaj", "📜・regulamin", "✅・akceptacja"}
    everyone = guild.default_role
    widz = discord.utils.get(guild.roles, name="👀 Widz")

    if widz is None:
        try:
            widz = await guild.create_role(
                name="👀 Widz",
                colour=discord.Colour(0x95A5A6),
                reason="ASAXES verification"
            )
        except Exception as e:
            print(f"Nie udało się utworzyć roli 👀 Widz: {e}", flush=True)
            widz = None

    for channel in guild.text_channels:
        try:
            if channel.name in visible_names:
                await channel.set_permissions(
                    everyone,
                    view_channel=True,
                    read_message_history=True,
                    send_messages=(channel.name == "👋・witaj")
                )
                if widz:
                    await channel.set_permissions(
                        widz,
                        view_channel=True,
                        read_message_history=True,
                        send_messages=(channel.name == "👋・witaj")
                    )
            else:
                await channel.set_permissions(
                    everyone,
                    view_channel=False
                )
                if widz:
                    await channel.set_permissions(
                        widz,
                        view_channel=True,
                        read_message_history=True,
                        send_messages=True
                    )
        except Exception as e:
            print(f"Nie udało się ustawić dostępu {channel.name}: {e}", flush=True)


def make_welcome_embed(guild):
    embed = discord.Embed(
        title="👋 WITAJ NA ASAXES",
        description=(
            "🎯 **Witamy na oficjalnym serwerze społeczności ASAXES.**\n\n"
            "🎮 To miejsce stworzone dla osób zainteresowanych **gamingiem, "
            "streamami oraz wspólną rozrywką**.\n\n"
            "🔐 **Zanim rozpoczniesz korzystanie z serwera:**\n"
            "├ 📜 Zapoznaj się z **regulaminem**\n"
            "├ ✅ Zaakceptuj regulamin w kanale **#・akceptacja**\n"
            "└ 🎭 Wybierz swoje **role i zainteresowania**\n\n"
            "💬 **Dołącz do społeczności**\n"
            "Poznaj nowych ludzi, porozmawiaj, graj razem i dziel się "
            "swoimi najlepszymi momentami.\n\n"
            "🔴 **STREAMY ASAXES**\n"
            "Nie przegap transmisji, wydarzeń oraz najważniejszych informacji "
            "związanych z kanałem.\n\n"
            "🛡️ Szanuj innych użytkowników, przestrzegaj zasad i dbajmy "
            "wspólnie o dobrą atmosferę.\n\n"
            "**⭐ ASAXES — Gaming • Community • Entertainment**"
        ),
        colour=discord.Colour(0x9B59B6)
    )
    embed.set_footer(text="ASAXES • Oficjalna społeczność")
    return embed

async def ensure_onboarding_messages(guild):
    welcome = discord.utils.get(guild.text_channels, name="👋・witaj")
    if welcome:
        found = False
        async for m in welcome.history(limit=30):
            if m.author.id == bot.user.id and m.embeds:
                if m.embeds[0].title in {"👋 WITAJ NA ASAXES", "🎉 WITAJ NA SERWERZE ASAXES! 🎉"}:
                    found = True
                    break
        if not found:
            await welcome.send(embed=make_welcome_embed(guild))

    acceptance = discord.utils.get(guild.text_channels, name="✅・akceptacja")
    if acceptance:
        found = False
        async for m in acceptance.history(limit=30):
            if m.author.id == bot.user.id and m.components:
                found = True
                break
        if not found:
            embed = discord.Embed(
                title="🔐 AKCEPTACJA REGULAMINU",
                description=(
                    "Przeczytaj dokładnie kanał **📜・regulamin**.\n\n"
                    "Jeżeli zgadzasz się z zasadami serwera, kliknij poniżej "
                    "przycisk **Akceptuję regulamin**.\n\n"
                    "✅ Po akceptacji otrzymasz rolę **👀 Widz** i uzyskasz dostęp "
                    "do pozostałych kanałów serwera."
                ),
                colour=discord.Colour(0x2ECC71)
            )
            await acceptance.send(embed=embed, view=VerifyView())

@bot.event
async def on_ready():
    bot.add_view(RoleView())
    bot.add_view(VerifyView())
    bot.add_view(TicketView())
    for guild in bot.guilds:
        try:
            # 📖 Kanały informacyjne systemu XP/punktów
            info_category = discord.utils.get(guild.categories, name="📌 INFORMACJE")
            rewards_category = discord.utils.get(guild.categories, name="🏆 NAGRODY")
            if rewards_category is None:
                rewards_category = discord.utils.get(guild.categories, name="🏆 NAGRODY")

            channel_specs = [
                ("📖・komendy", "📖 Wszystkie komendy ASAXES — sprawdź tutaj co możesz używać.", info_category),
                ("🏆・ranking", "🏆 Ranking aktywności — !rank, !top, !nagrody", rewards_category),
                ("💰・punkty", "💰 Twoje punkty — użyj !punkty", rewards_category),
                ("🛒・sklep", "🛒 Sklep ASAXES — sprawdź nagrody i użyj !kup nazwa", rewards_category),
                ("🎁・nagrody", "🎁 Nagrody za poziomy i aktywność — użyj !nagrody", rewards_category),
            ]

            created_channels = {}
            for name, topic, category in channel_specs:
                ch = discord.utils.get(guild.text_channels, name=name)
                if ch is None:
                    ch = await guild.create_text_channel(
                        name,
                        topic=topic,
                        category=category,
                        reason="ASAXES system XP/punkty"
                    )
                created_channels[name] = ch

            # 📖 Instrukcja komend — wysyłana tylko jeśli kanał nie ma jeszcze panelu.
            commands_ch = created_channels["📖・komendy"]
            has_commands_panel = False
            async for m in commands_ch.history(limit=30):
                if m.author.id == bot.user.id and m.embeds and m.embeds[0].title == "📖 KOMENDY ASAXES":
                    has_commands_panel = True
                    break
            if not has_commands_panel:
                embed = discord.Embed(
                    title="📖 KOMENDY ASAXES",
                    description="""### 🏆 Aktywność
`!rank` — Twój poziom, XP i punkty
`!top` — TOP 10 aktywnych osób
`!punkty` — sprawdź swoje punkty

### 🛒 Sklep
`!sklep` — zobacz dostępne nagrody
`!kup vip` — kup VIP
`!kup wspierajacy` — kup Wspierającego
`!kup czerwony` — kup czerwoną rolę
`!kup niebieski` — kup niebieską rolę
`!kup fioletowy` — kup fioletową rolę
`!kup zielony` — kup zieloną rolę

### 🎁 Nagrody
`!nagrody` — zobacz nagrody za poziomy

💡 **Jak zdobywać XP i punkty?**
Bądź aktywny na serwerze — pisz, rozmawiaj i graj razem ze społecznością! 🎮💬""",
                    colour=discord.Colour(0x9B59B6)
                )
                embed.set_footer(text="ASAXES • System aktywności")
                await commands_ch.send(embed=embed)

            # 🛒 Panel sklepu
            shop_ch = created_channels["🛒・sklep"]
            has_shop_panel = False
            async for m in shop_ch.history(limit=30):
                if m.author.id == bot.user.id and m.embeds and m.embeds[0].title == "🛒 SKLEP ASAXES":
                    has_shop_panel = True
                    break
            if not has_shop_panel:
                await shop_ch.send(embed=discord.Embed(
                    title="🛒 SKLEP ASAXES",
                    description="""💎 **VIP** — 1000 pkt → `!kup vip`
💜 **Wspierający** — 500 pkt → `!kup wspierajacy`
🔴 **Czerwony** — 200 pkt → `!kup czerwony`
🔵 **Niebieski** — 200 pkt → `!kup niebieski`
🟣 **Fioletowy** — 200 pkt → `!kup fioletowy`
🟢 **Zielony** — 200 pkt → `!kup zielony`

💰 Punkty zdobywasz za aktywność na serwerze.""",
                    colour=discord.Colour(0xE67E22)
                ))

            # 🏆 Panel rankingu
            ranking_ch = created_channels["🏆・ranking"]
            has_rank_panel = False
            async for m in ranking_ch.history(limit=30):
                if m.author.id == bot.user.id and m.embeds and m.embeds[0].title == "🏆 RANKING AKTYWNOŚCI":
                    has_rank_panel = True
                    break
            if not has_rank_panel:
                await ranking_ch.send(embed=discord.Embed(
                    title="🏆 RANKING AKTYWNOŚCI",
                    description="""⭐ Sprawdź swój wynik: `!rank`
🏆 Zobacz TOP 10: `!top`

💡 Im większa aktywność, tym więcej XP i punktów!""",
                    colour=discord.Colour(0xF1C40F)
                ))

            await configure_new_user_visibility(guild)
            await ensure_onboarding_messages(guild)
        except Exception as e:
            print(f"BŁĄD ONBOARDINGU {guild.name}: {e!r}", flush=True)
    print(f"BOT ONLINE: {bot.user}")
    for guild in bot.guilds:
        ch=discord.utils.get(guild.text_channels,name="🎭・wybierz-role")
        if not ch:
            print("Nie znaleziono kanału 🎭・wybierz-role")
            continue

        # Usuwamy stare panele bota, aby nie zostały stare komponenty.
        async for m in ch.history(limit=50):
            if m.author.id==bot.user.id:
                try: await m.delete()
                except: pass

        embed=discord.Embed(
            title="🎭 WYBIERZ SWOJE ROLE",
            description=(
                "**🎮 Gry** — wybierz gry, które lubisz.\n"
                "**🎵 Zainteresowania** — pokaż swoje zainteresowania.\n"
                "**🔔 Powiadomienia** — wybierz, o czym chcesz dostawać informacje.\n"
                "**🎨 Kolory** — wybierz kolor.\n\n"
                "Kliknij ponownie, aby usunąć rolę."
            ))
        await ch.send(embed=embed,view=RoleView())
        print(f"NOWY PANEL GOTOWY: {guild.name}")
    print("GOTOWE — kliknij teraz dowolną rolę.")

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="👋・witaj")
    if not channel:
        return

    embed = discord.Embed(
        title="🎉 WITAJ NA SERWERZE ASAXES! 🎉",
        description=(
            f"👋 **Witaj, {member.mention}!**\n\n"
            "🎯 **Witamy na oficjalnym serwerze społeczności ASAXES.**\n\n"
            "🎮 To miejsce stworzone dla osób zainteresowanych **gamingiem, "
            "streamami oraz wspólną rozrywką**.\n\n"
            "🔐 **Zanim rozpoczniesz korzystanie z serwera:**\n"
            "├ 📜 Zapoznaj się z **regulaminem**\n"
            "├ ✅ Zaakceptuj regulamin\n"
            "└ 🎭 Wybierz swoje **role i zainteresowania**\n\n"
            "💬 **Dołącz do społeczności**\n"
            "Poznaj nowych ludzi, porozmawiaj, graj razem i dziel się "
            "swoimi najlepszymi momentami.\n\n"
            "🔴 **STREAMY ASAXES**\n"
            "Nie przegap transmisji, wydarzeń oraz najważniejszych informacji "
            "związanych z kanałem.\n\n"
            "🛡️ Szanuj innych użytkowników, przestrzegaj zasad i dbajmy "
            "wspólnie o dobrą atmosferę.\n\n"
            "**⭐ ASAXES — Gaming • Community • Entertainment**"
        ),
        colour=discord.Colour(0x9B59B6)
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"ASAXES • Użytkownik #{member.guild.member_count}")

    await channel.send(embed=embed)

    log_channel = discord.utils.get(member.guild.text_channels, name="📋・logi")
    if log_channel:
        await log_channel.send(
            f"👋 **Nowy użytkownik**\n"
            f"👤 {member.mention}\n"
            f"🏠 Dołączył na serwer ASAXES"
        )

bot.run(TOKEN)

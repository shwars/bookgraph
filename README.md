# Бесприданница — wiki и граф книги

Откройте каталог `D:\GIT\bookgraph` как vault в Obsidian. Начните с [путеводителя по действиям](wiki/books/bespridannica-guide.md) или [индекса](wiki/index.md). Карточки и пояснения написаны по-русски; граф охватывает пьесу, редакционный комментарий и все 11 примечаний предоставленного издания.

[Акварельные персонажи и фоны](wiki/illustrations.bespridannica.md) · [Состав, возрастные ориентиры и структура изображений](work/illustrations/README.md). Иллюстрации также находятся в ручных разделах карточек персонажей и мест.

- [Порядок изложения и повторные появления](wiki/book-timeline.bespridannica.md)
- [Календарный таймлайн](wiki/cal-timeline.md) и [датировки редакционного аппарата](wiki/books/bespridannica-guide.md#хронология-редакционного-аппарата--не-события-пьесы)
- [Покрытие чтения, извлечения и аудита](wiki/coverage.bespridannica.md)
- [Смысловой аудит и неопределённости](wiki/audit.bespridannica.md), [проверка примечаний](wiki/notes-audit.bespridannica.md), [техническая проверка](wiki/verification.bespridannica.md)
- [Структура: действие → явление → стабильный адрес](source/bespridannica/structure.md)
- [Экспорт графа](wiki/graph.json), [таблица Obsidian Bases](wiki/views/concepts.base), [словарь связей](wiki/predicates.md)

В Obsidian используйте Graph view и локальный граф карточки. Для просмотра только wiki можно задать поисковый фильтр `path:wiki`; подготовленный текст находится в `source/`. В JSON типы связей и статусы доступны явно. Ручные Markdown-карточки — источник данных; JSON, обратные связи и служебные индексы пересобираются.

Оригинальный архив в `raw/` сохранён без изменений. Из него извлечён FB2; хеши и описание издания записаны в [реестре происхождения](source/provenance.json). Исторический аппарат имеет `scope: editorial`: внешнее исследование не выполнялось. Точная дата действия не назначена по дате написания пьесы.

В подготовленном Markdown исправлены тройные скобки у 11 ссылок на примечания; исходный текст атомов и адреса сохранены. [Журнал исправления отображения](source/bespridannica/display-normalization.json) фиксирует каждую замену. Если заново запускать `prepare`, затем выполните `python scripts/fix_note_display.py`.

## Офлайн-приложение

Откройте [атлас книги](viewer/index.html) двойным кликом: граф персонажей, хронология событий по тексту, граф зависимостей и читалка пьесы. Интернет и сервер для просмотра не нужны. [Инструкция и обновление данных](viewer/README.md) · [Смысловая проверка обогащения](wiki/viewer-audit.bespridannica.md).

## Проверка и пересборка

Требуются Python 3.10+ и PyYAML 6.x. Используется установленный скилл wikibook; движок в проект заново не копировался. Уже имеющийся каталог `skills/` оставлен без изменений.

```powershell
python "$env:USERPROFILE\.codex\skills\wikibook\scripts\wiki.py" --root D:\GIT\bookgraph status --book-id bespridannica
python "$env:USERPROFILE\.codex\skills\wikibook\scripts\wiki.py" --root D:\GIT\bookgraph validate
python "$env:USERPROFILE\.codex\skills\wikibook\scripts\wiki.py" --root D:\GIT\bookgraph build
python scripts/check_vault.py
```

Полная проверка повторяемости сборки и запись технического отчёта:

```powershell
python scripts/check_vault.py --rebuild-check --write-report
```

Для другого расположения скилла передайте `--skill C:\path\to\wikibook`. Проверка читает данные из Markdown через API скилла, сверяет ZIP/FB2, все 50 единиц, 11 примечаний, ссылки и экспорт. При проверке повторяемости выполняются две сборки, сравниваются результаты и сохранность ручного текста. Проверка не выставляет флаги смыслового аудита.

Итоги и пределы полноты указаны в отчётах: завершённые стадии покрытия не означают отсутствия любой возможной интерпретации или неоднозначности литературного текста.


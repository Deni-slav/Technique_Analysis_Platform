# Качване в GitHub

Репозиторият е готов за качване. Следвайте тези стъпки:

## 1. Създайте ново хранилище на GitHub

1. Отидете на https://github.com/new
2. Име на репозитория: `RowingAnalysis` (или друго по избор)
3. Оставете празно (без README, .gitignore)
4. Натиснете **Create repository**

## 2. Свържете и качете

В терминал (от папката на проекта) изпълнете:

```bash
git remote add origin https://github.com/VASHET_GITHUB_USERNAME/RowingAnalysis.git
git branch -M main
git push -u origin main
```

**Замените** `VASHET_GITHUB_USERNAME` с вашето потребителско име в GitHub!

## Алтернатива с SSH

Ако използвате SSH ключ:

```bash
git remote add origin git@github.com:VASHET_GITHUB_USERNAME/RowingAnalysis.git
git branch -M main
git push -u origin main
```

/*******************************************************************************
 * Copyright (c) 2022 Nerian Vision GmbH
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *******************************************************************************/

#ifndef SETTINGSDIALOG_H
#define SETTINGSDIALOG_H

#include <QDialog>
#include "settings.h"

namespace Ui {
class SettingsDialog;
}

class SettingsDialog : public QDialog
{
    Q_OBJECT

public:
    explicit SettingsDialog(QWidget *parent, const Settings& settings);
    ~SettingsDialog();

    const Settings& getSettings();
    static bool chooseWriteDirectory(QWidget *parent, Settings& settings, bool allowSkip);

private:
    Ui::SettingsDialog *ui;
    Settings settingsNew;
    Settings settingsOrig;
    bool accepted;

    void dialogAccepted();
    void adjustSize();
};

#endif // SETTINGSDIALOG_H
